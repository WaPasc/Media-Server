#include "MpvItem.h"

#include <QQuickWindow>
#include <QOpenGLContext>
#include <QOpenGLFunctions>
#include <rhi/qrhi_platform.h>  // QRhiTexture (full definition), QRhiGles2NativeHandles
#include <stdexcept>
#include <vector>

// Provides OpenGL function pointers to mpv during mpv_render_context_create().
// ctx is the QOpenGLContext* passed through mpv_opengl_init_params::get_proc_address_ctx.
static void *get_proc_address_mpv(void *ctx, const char *name)
{
    auto *glctx = static_cast<QOpenGLContext *>(ctx);
    if (!glctx)
        return nullptr;
    return reinterpret_cast<void *>(glctx->getProcAddress(QByteArray(name)));
}

// ─── MpvRenderer ─────────────────────────────────────────────────────────────
//
// Lives entirely on the render thread. Qt calls initialize() when the target
// texture size changes, synchronize() each frame (main thread blocked, safe to
// read item state), and render() to produce the frame.
//
// Design: we create our own GL framebuffer object (FBO) that wraps Qt's managed
// color texture.  mpv renders into that FBO via its OpenGL render API, and Qt
// composites the texture into the scene graph afterwards.

class MpvRenderer : public QQuickRhiItemRenderer
{
    MpvItem *m_item;

    // Our GL FBO wrapping Qt's colorTexture(). Recreated on every resize.
    GLuint m_fbo     = 0;
    QSize  m_fboSize;

    // Snapshot of MpvItem::m_videoReady, copied in synchronize().
    bool m_videoReady = false;

public:
    explicit MpvRenderer(MpvItem *item) : m_item(item) {}

    ~MpvRenderer() override
    {
        deleteFbo();
    }

    // ── synchronize ──────────────────────────────────────────────────────────
    // Called each frame with the main thread blocked.  Safe to read item data.
    void synchronize(QQuickRhiItem *rhiItem) override
    {
        m_videoReady = static_cast<MpvItem *>(rhiItem)->m_videoReady;
    }

    // ── initialize ───────────────────────────────────────────────────────────
    // Called on the render thread when the color texture changes size or on
    // first use.  No QRhi render pass is active — safe for raw OpenGL calls.
    void initialize(QRhiCommandBuffer * /*cb*/) override
    {
        // One-time: create mpv's OpenGL render context bound to Qt's GL context.
        if (!m_item->m_mpvGl) {
            // Retrieve the QOpenGLContext from the RHI instance.  This is the
            // authoritative way when using QQuickRhiItem — it works even if Qt
            // changes how it manages context currency in a future version.
            const auto *glHandles = static_cast<const QRhiGles2NativeHandles *>(
                rhi()->nativeHandles()
            );

            mpv_opengl_init_params glInitParams{
                get_proc_address_mpv,
                glHandles->context  // passed as 'ctx' to get_proc_address_mpv
            };
            mpv_render_param params[] = {
                {MPV_RENDER_PARAM_API_TYPE,           const_cast<char *>(MPV_RENDER_API_TYPE_OPENGL)},
                {MPV_RENDER_PARAM_OPENGL_INIT_PARAMS, &glInitParams},
                {MPV_RENDER_PARAM_INVALID,            nullptr}
            };

            if (mpv_render_context_create(&m_item->m_mpvGl, m_item->m_mpv, params) < 0)
                throw std::runtime_error("failed to initialize mpv GL context");

            mpv_render_context_set_update_callback(
                m_item->m_mpvGl, MpvItem::on_mpv_redraw, m_item
            );
        }

        // (Re-)create our GL FBO whenever Qt's managed texture changes size.
        const QSize newSize = colorTexture()->pixelSize();
        if (newSize != m_fboSize)
            recreateFbo(newSize);
    }

    // ── render ───────────────────────────────────────────────────────────────
    // Called on the render thread each frame.  No QRhi render pass is active.
    void render(QRhiCommandBuffer * /*cb*/) override
    {
        mpv_opengl_fbo mpFbo{
            static_cast<int>(m_fbo),
            m_fboSize.width(),
            m_fboSize.height(),
            0               // internal_format — 0 means "let mpv decide" (RGBA8)
        };
        // QQuickRhiItem expects textures in top-left-origin (RHI/D3D/Metal style).
        // mpv natively renders bottom-left-origin (standard OpenGL).  flip_y = 1
        // tells mpv to flip its output so Qt composites it the right way up.
        int flipY = 1;
        mpv_render_param params[] = {
            {MPV_RENDER_PARAM_OPENGL_FBO, &mpFbo},
            {MPV_RENDER_PARAM_FLIP_Y,     &flipY},
            {MPV_RENDER_PARAM_INVALID,    nullptr}
        };

        // Always call render to keep consuming mpv's decoded frame queue.
        // Stalling the queue would eventually stall mpv's decoder thread.
        mpv_render_context_render(m_item->m_mpvGl, params);

        // GPU-level fix for the "previous video last frame flash":
        // Between MPV_EVENT_START_FILE and the first decoded frame of the new
        // video, mpv renders the old last frame into our FBO.  We overwrite it
        // with black so the stale frame is never composited onto the screen.
        if (!m_videoReady) {
            auto *f = QOpenGLContext::currentContext()->functions();
            f->glBindFramebuffer(GL_FRAMEBUFFER, m_fbo);
            f->glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
            f->glClear(GL_COLOR_BUFFER_BIT);
            f->glBindFramebuffer(GL_FRAMEBUFFER, 0);
        }
    }

private:
    // Create a new GL FBO whose color attachment is Qt's managed color texture.
    // Multiple FBOs can reference the same GL texture without conflict.
    void recreateFbo(const QSize &size)
    {
        auto *f = QOpenGLContext::currentContext()->functions();

        if (m_fbo) {
            f->glDeleteFramebuffers(1, &m_fbo);
            m_fbo = 0;
        }

        const auto texId = static_cast<GLuint>(colorTexture()->nativeTexture().object);

        f->glGenFramebuffers(1, &m_fbo);
        f->glBindFramebuffer(GL_FRAMEBUFFER, m_fbo);
        f->glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                                  GL_TEXTURE_2D, texId, 0);
        f->glBindFramebuffer(GL_FRAMEBUFFER, 0);

        m_fboSize = size;
    }

    void deleteFbo()
    {
        if (!m_fbo)
            return;
        if (auto *ctx = QOpenGLContext::currentContext())
            ctx->functions()->glDeleteFramebuffers(1, &m_fbo);
        m_fbo = 0;
    }
};

// ─── MpvItem (main thread) ────────────────────────────────────────────────────

MpvItem::MpvItem(QQuickItem *parent)
    : QQuickRhiItem(parent), m_mpv(mpv_create())
{
    if (!m_mpv)
        throw std::runtime_error("could not create mpv context");

    mpv_set_option_string(m_mpv, "terminal", "yes");
    mpv_set_option_string(m_mpv, "msg-level", "all=info");

    // Tell mpv to output video via our custom OpenGL bridge
    mpv_set_option_string(m_mpv, "vo", "libmpv");

    // Enable hardware-accelerated decoding (VAAPI/NVDEC on Linux, VideoToolbox on
    // macOS, DXVA2/D3D11VA on Windows).  Falls back to software if unavailable.
    mpv_set_option_string(m_mpv, "hwdec", "auto");

    mpv_observe_property(m_mpv, 0, "time-pos", MPV_FORMAT_DOUBLE);
    mpv_observe_property(m_mpv, 0, "duration", MPV_FORMAT_DOUBLE);

    mpv_set_wakeup_callback(m_mpv, on_mpv_wakeup, this);

    if (mpv_initialize(m_mpv) < 0)
        throw std::runtime_error("could not initialize mpv context");

    connect(this, &MpvItem::onUpdate, this, &MpvItem::doUpdate, Qt::QueuedConnection);
}

MpvItem::~MpvItem()
{
    // m_mpvGl must be freed before mpv_terminate_destroy().
    // The renderer is destroyed by Qt before this destructor runs (render thread
    // teardown precedes QML engine teardown), so m_mpvGl is no longer in use.
    if (m_mpvGl)
        mpv_render_context_free(m_mpvGl);
    mpv_terminate_destroy(m_mpv);
}

QQuickRhiItemRenderer *MpvItem::createRenderer()
{
    return new MpvRenderer(this);
}

// Called by mpv on a background thread when a new frame is ready.
void MpvItem::on_mpv_redraw(void *ctx)
{
    emit static_cast<MpvItem *>(ctx)->onUpdate();
}

// Runs on the GUI thread — tells Qt to schedule a repaint of this item.
void MpvItem::doUpdate()
{
    update();
}

// Called from any background thread when mpv queues a new event.
void MpvItem::on_mpv_wakeup(void *ctx)
{
    QMetaObject::invokeMethod(
        static_cast<MpvItem *>(ctx), "processMpvEvents", Qt::QueuedConnection
    );
}

// Drains mpv's event queue on the GUI thread.
void MpvItem::processMpvEvents()
{
    while (m_mpv) {
        mpv_event *event = mpv_wait_event(m_mpv, 0);
        if (event->event_id == MPV_EVENT_NONE)
            break;
        handleMpvEvent(event);
    }
}

void MpvItem::handleMpvEvent(mpv_event *event)
{
    switch (event->event_id) {

    case MPV_EVENT_START_FILE:
        // A new file is beginning to load.  Hide the previous video's last frame
        // until the first decoded frame of the new video arrives.
        if (m_videoReady) {
            m_videoReady = false;
            emit videoReadyChanged();
        }
        break;

    case MPV_EVENT_PROPERTY_CHANGE: {
        auto *prop = static_cast<mpv_event_property *>(event->data);

        if (strcmp(prop->name, "time-pos") == 0 && prop->format == MPV_FORMAT_DOUBLE) {
            emit timeChanged(*static_cast<double *>(prop->data));

            // The first time-pos tick signals that the new video's first frame
            // has been decoded and handed to the renderer.  Lift the black cover.
            if (!m_videoReady) {
                m_videoReady = true;
                emit videoReadyChanged();
            }

        } else if (strcmp(prop->name, "duration") == 0 && prop->format == MPV_FORMAT_DOUBLE) {
            emit durationChanged(*static_cast<double *>(prop->data));
        }
        break;
    }

    default:
        break;
    }
}

// ─── QML-invokable helpers ────────────────────────────────────────────────────

void MpvItem::command(const QVariantList &params)
{
    std::vector<QByteArray>   bytes;
    std::vector<const char *> args;
    bytes.reserve(params.size());
    args.reserve(params.size() + 1);

    for (const auto &param : params) {
        bytes.push_back(param.toString().toUtf8());
        args.push_back(bytes.back().constData());
    }
    args.push_back(nullptr);

    // Hide the previous video the moment a load/stop is requested — don't wait
    // for MPV_EVENT_START_FILE.  That event arrives asynchronously, so between
    // the user's click and mpv's event we'd otherwise still composite frames
    // from the previous video.
    if (!bytes.empty() && m_videoReady) {
        const QByteArray &cmd = bytes.front();
        if (cmd == "loadfile" || cmd == "stop") {
            m_videoReady = false;
            emit videoReadyChanged();
        }
    }

    mpv_command_async(m_mpv, 0, args.data());
}

void MpvItem::setProperty(const QString &name, const QVariant &value)
{
    const QByteArray nameBytes  = name.toUtf8();
    const QByteArray valueBytes = value.toString().toUtf8();
    mpv_set_property_string(m_mpv, nameBytes.constData(), valueBytes.constData());
}
