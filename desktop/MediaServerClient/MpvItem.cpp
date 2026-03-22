#include "MpvItem.h"

#include <QQuickWindow>
#include <QOpenGLContext>
#include <QOpenGLFramebufferObject>
#include <QQuickOpenGLUtils>
#include <stdexcept>
#include <vector>

// 1. THE OPENGL TRANSLATOR (Runs on Render Thread)
// libmpv needs to know how to talk to specific GPU (NVIDIA/Intel).
// This function grabs the raw OpenGL memory addresses directly from Qt.
static void *get_proc_address_mpv(void *ctx, const char *name)
{
    Q_UNUSED(ctx)
    QOpenGLContext *glctx = QOpenGLContext::currentContext();
    if (!glctx) return nullptr;
    return reinterpret_cast<void *>(glctx->getProcAddress(QByteArray(name)));
}

// 2. THE BACKGROUND RENDERER (Runs on Render Thread)
class MpvRenderer : public QQuickFramebufferObject::Renderer
{
    MpvItem *item;

public:
    MpvRenderer(MpvItem *new_item) : item{new_item} {}
    ~MpvRenderer() override {}

    // Called by Qt the very first time it tries to draw the video player.
    QOpenGLFramebufferObject *createFramebufferObject(const QSize &size) override
    {
        // If the mpv OpenGL context doesn't exist yet, create it
        if (!item->mpv_gl)
        {
            mpv_opengl_init_params gl_init_params{get_proc_address_mpv, nullptr};
            mpv_render_param params[]{
                {MPV_RENDER_PARAM_API_TYPE, const_cast<char *>(MPV_RENDER_API_TYPE_OPENGL)},
                {MPV_RENDER_PARAM_OPENGL_INIT_PARAMS, &gl_init_params},
                {MPV_RENDER_PARAM_INVALID, nullptr}
            };

            if (mpv_render_context_create(&item->mpv_gl, item->mpv, params) < 0)
                throw std::runtime_error("failed to initialize mpv GL context");

            // Tell mpv to call our redraw function whenever a frame is ready
            mpv_render_context_set_update_callback(item->mpv_gl, MpvItem::on_mpv_redraw, item);

            // Tell QML that GPU canvas is built
            QMetaObject::invokeMethod(item, "ready", Qt::QueuedConnection);
        }

        return QQuickFramebufferObject::Renderer::createFramebufferObject(size);
    }

    // Called x times a second to paint the actual pixels
    void render() override
    {
        // 1. Reset state using the Qt 6 Utility
        QQuickOpenGLUtils::resetOpenGLState();

        QOpenGLFramebufferObject *fbo = framebufferObject();
        mpv_opengl_fbo mpfbo{
            static_cast<int>(fbo->handle()),
            fbo->width(),
            fbo->height(),
            0
        };

        // make sure have the right flip for y so the video is not flipped around y-axis
        int flip_y{0};

        mpv_render_param params[] = {
            {MPV_RENDER_PARAM_OPENGL_FBO, &mpfbo},
            {MPV_RENDER_PARAM_FLIP_Y, &flip_y},
            {MPV_RENDER_PARAM_INVALID, nullptr}
        };

        mpv_render_context_render(item->mpv_gl, params);

        // 2. Reset state again after mpv is done drawing
        QQuickOpenGLUtils::resetOpenGLState();
    }
};

// 3. THE QML FRONTEND BRIDGE (Runs on Main GUI Thread)
MpvItem::MpvItem(QQuickItem *parent)
    : QQuickFramebufferObject(parent), mpv{mpv_create()}, mpv_gl(nullptr)
{
    if (!mpv) throw std::runtime_error("could not create mpv context");

    // Debugging
    mpv_set_option_string(mpv, "terminal", "yes");
    mpv_set_option_string(mpv, "msg-level", "all=info");

    // Tell mpv to output video via our custom OpenGL bridge
    mpv_set_option_string(mpv, "vo", "libmpv");
    // Enable Hardware Acceleration (VAAPI/NVDEC) for your Linux GPU!
    mpv_set_option_string(mpv, "hwdec", "auto");

    mpv_observe_property(mpv, 0, "time-pos", MPV_FORMAT_DOUBLE);
    mpv_observe_property(mpv, 0, "duration", MPV_FORMAT_DOUBLE);

    mpv_set_wakeup_callback(mpv, on_mpv_wakeup, this);

    if (mpv_initialize(mpv) < 0)
        throw std::runtime_error("could not initialize mpv context");

    // Wire up the thread-safe communication
    connect(this, &MpvItem::onUpdate, this, &MpvItem::doUpdate, Qt::QueuedConnection);
}

MpvItem::~MpvItem()
{
    if (mpv_gl) mpv_render_context_free(mpv_gl);
    mpv_terminate_destroy(mpv);
}

// Creates the background renderer and passes it to Qt
QQuickFramebufferObject::Renderer *MpvItem::createRenderer() const
{
    window()->setPersistentGraphics(true);
    window()->setPersistentSceneGraph(true);
    return new MpvRenderer(const_cast<MpvItem *>(this));
}

// Called by mpv on a background thread. Emits a signal to wake up the GUI thread.
void MpvItem::on_mpv_redraw(void *ctx)
{
    MpvItem *self = static_cast<MpvItem *>(ctx);
    emit self->onUpdate();
}

// Called on the GUI thread. Tells Qt "Please redraw this component!"
void MpvItem::doUpdate()
{
    update();
}

// Called from any background thread when mpv has a new event (like a clock tick)
void MpvItem::on_mpv_wakeup(void *ctx)
{
    MpvItem *self = static_cast<MpvItem *>(ctx);
    // Safely ask the main GUI thread to process the events
    QMetaObject::invokeMethod(self, "processMpvEvents", Qt::QueuedConnection);
}

// Runs on the GUI Thread. Empties the mpv event queue.
void MpvItem::processMpvEvents()
{
    while (mpv) {
        mpv_event *event = mpv_wait_event(mpv, 0);
        if (event->event_id == MPV_EVENT_NONE) break; // Queue is empty
        handleMpvEvent(event);
    }
}

// Translates raw C properties into QML signals
void MpvItem::handleMpvEvent(mpv_event *event)
{
    if (event->event_id == MPV_EVENT_PROPERTY_CHANGE) {
        mpv_event_property *prop = static_cast<mpv_event_property *>(event->data);

        // Did the current time change?
        if (strcmp(prop->name, "time-pos") == 0 && prop->format == MPV_FORMAT_DOUBLE) {
            emit timeChanged(*(double *)prop->data);
        }
        // Did the total duration change?
        else if (strcmp(prop->name, "duration") == 0 && prop->format == MPV_FORMAT_DOUBLE) {
            emit durationChanged(*(double *)prop->data);
        }
    }
}

// --- JAVASCRIPT EXPOSED FUNCTIONS ---

// Allows us to call myVideo.command(["loadfile", "movie.mkv"]) from QML
void MpvItem::command(const QVariantList &params)
{
    std::vector<QByteArray> bytes;
    std::vector<const char *> args;
    for (const auto &param : params) {
        bytes.push_back(param.toString().toUtf8());
        args.push_back(bytes.back().constData());
    }
    args.push_back(nullptr);
    mpv_command_async(mpv, 0, args.data());
}

// Allows us to call myVideo.setProperty("pause", "no") from QML
void MpvItem::setProperty(const QString &name, const QVariant &value)
{
    QByteArray nameBytes = name.toUtf8();
    QByteArray valueBytes = value.toString().toUtf8();
    mpv_set_property_string(mpv, nameBytes.constData(), valueBytes.constData());
}

