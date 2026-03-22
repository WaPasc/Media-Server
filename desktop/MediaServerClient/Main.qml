import QtQuick
import QtQuick.Window
import MediaServerClient // This is the module name defined in CMakeLists.txt

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

        // Wait until C++ background thread tells us canvas is built
        onReady: {
            // call Q_INVOKABLE C++ function from JavaScript
            // standard open-source test video URL
            videoPlayer.command(["loadfile", "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"]);
        }

        // A simple invisible click area over the whole video
        MouseArea {
            anchors.fill: parent
            property bool isPaused: false

            onClicked: {
                isPaused = !isPaused;
                // This routes directly to C++ setProperty function
                videoPlayer.setProperty("pause", isPaused ? "yes" : "no");
            }
        }
    }
}