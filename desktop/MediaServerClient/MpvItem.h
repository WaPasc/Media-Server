#pragma once

#include <QQuickRhiItem>
#include <QVariantList>
#include <QString>
#include <mpv/client.h>
#include <mpv/render_gl.h>

// QQuickRhiItem integrates custom rendering with Qt Quick's RHI scene graph.
// It replaces the deprecated QQuickFramebufferObject (removed in Qt 6.7).
// libmpv only exposes an OpenGL render API, so we still force OpenGL as the
// RHI backend in main.cpp — the benefit here is using the correct Qt 6 class.
class MpvItem : public QQuickRhiItem
{
    Q_OBJECT
    // Exposed to QML so a black overlay can hide the scene graph's cached
    // texture (the previous video's last frame) during loading.
    Q_PROPERTY(bool videoReady READ videoReady NOTIFY videoReadyChanged)

public:
    explicit MpvItem(QQuickItem *parent = nullptr);
    ~MpvItem() override;

    // Called by Qt on the render thread to create the renderer object.
    QQuickRhiItemRenderer *createRenderer() override;

    bool videoReady() const { return m_videoReady; }

    // Exposed to QML/JS via MpvVideo { id: player }
    Q_INVOKABLE void command(const QVariantList &params);
    Q_INVOKABLE void setProperty(const QString &name, const QVariant &value);

signals:
    // Internal: mpv background thread -> Qt GUI thread redraw request.
    void onUpdate();

    // QML-facing: emitted when mpv reports a new playback position / duration.
    void timeChanged(double time);
    void durationChanged(double duration);

    void videoReadyChanged();

private slots:
    void doUpdate();
    void processMpvEvents();

private:
    mpv_handle         *m_mpv   = nullptr;
    mpv_render_context *m_mpvGl = nullptr;

    // Set false when a new file starts loading (MPV_EVENT_START_FILE).
    // Set true on the first decoded frame (first time-pos property change).
    // The renderer reads this via synchronize() to decide whether to clear
    // the FBO to black, hiding the previous video's last frame during load.
    bool m_videoReady = false;

    static void on_mpv_redraw(void *ctx);
    static void on_mpv_wakeup(void *ctx);
    void handleMpvEvent(mpv_event *event);

    friend class MpvRenderer;
};
