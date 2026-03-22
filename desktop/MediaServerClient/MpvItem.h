#pragma once

#include <QtQuick/QQuickFramebufferObject>
#include <QVariantList>
#include <QString>
#include <mpv/client.h>
#include <mpv/render_gl.h>

// QQuickFramebufferObject for integrating OpenGL rendering using
// a framebuffer object with Qt Quick
class MpvItem : public QQuickFramebufferObject
{
    Q_OBJECT

public:
    explicit MpvItem(QQuickItem *parent = nullptr);
    ~MpvItem() override;

    // Override Qt function, hands rendering off to background OpenGL thread
    Renderer *createRenderer() const override;

    // Q_INVOKABLE exposes cpp functions to frontend QML/js
    Q_INVOKABLE void command(const QVariantList &params);
    Q_INVOKABLE void setProperty(const QString &name, const QVariant &value);

// signals are to broadcast something
signals:
    // mpv decodes frames on its own background threads, it uses
    // this signal to tell Qt GUI thread that there is a new frame
    void onUpdate();

// receiver for signals
private slots:
    // tells Qt to update the screen
    void doUpdate();

private:
    mpv_handle *mpv;
    mpv_render_context *mpv_gl;

    // static callback function that mpv can call from any thread
    static void on_mpv_redraw(void *ctx);

    // MpvRenderer friend so the background render thread
    // is allowed to acces our private mpv pointers.
    friend class MpvRenderer;


};
