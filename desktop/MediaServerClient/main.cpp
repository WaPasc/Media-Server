#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQuickWindow>
#include <clocale>


#include "MpvItem.h"

int main(int argc, char *argv[])
{
    // FORCE OPENGL: tells Qt 6's new RHI engine to fall back to OpenGL.
    // Must be called before creating QGuiApplication
    QQuickWindow::setGraphicsApi(QSGRendererInterface::OpenGL);

    QGuiApplication app(argc, argv);

    // Qt sets the locale in the QGuiApplication constructor, but libmpv
    // requires the LC_NUMERIC category to be set to "C", so change it back
    std::setlocale(LC_NUMERIC, "C");

    // REGISTER COMPONENT: tells QML that our C++ class exists
    // QML will be able to create an element called "MpvVideo"
    qmlRegisterType<MpvItem>("MediaServerClient", 1, 0, "MpvVideo");

    QQmlApplicationEngine engine;
    QObject::connect(
        &engine,
        &QQmlApplicationEngine::objectCreationFailed,
        &app,
        []() { QCoreApplication::exit(-1); },
        Qt::QueuedConnection);
    engine.loadFromModule("MediaServerClient", "Main");

    return QCoreApplication::exec();
}
