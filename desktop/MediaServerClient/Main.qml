import QtQuick
import QtQuick.Window
import MediaServerClient // This is the module name we defined in CMakeLists.txt!

Window {
    width: 1280
    height: 720
    visible: true
    title: "Pop!_OS Media Player"
    color: "black" // A nice dark background for our theater

    // Custom C++ Component, declared in main.cpp
    MpvVideo {
        id: videoPlayer
        anchors.fill: parent // Tell it to fill the entire window

        // This runs the exact millisecond the UI finishes loading
        Component.onCompleted: {
            // call Q_INVOKABLE C++ function from JavaScript!
            // standard open-source test video URL
            videoPlayer.command(["loadfile", "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"]);
        }
    }
}