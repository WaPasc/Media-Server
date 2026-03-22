import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import MediaServerClient // This is the module name defined in CMakeLists.txt

Window {
    id: mainWindow
    width: 1280
    height: 720
    visible: true
    title: "Pop!_OS Media Player"
    color: "black" // dark background

    property bool cursorVisible: true

    // JavaScript helper to turn raw seconds into text
    function formatTime(timeInSeconds) {
        if (isNaN(timeInSeconds) || timeInSeconds < 0)
            return "00:00";
        let m = Math.floor(timeInSeconds / 60);
        let s = Math.floor(timeInSeconds % 60);
        return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
    }

    // Press 'F' or 'F11' to toggle fullscreen
    Shortcut {
        sequence: "F" // You can also use StandardKey.FullScreen
        onActivated: toggleFullscreen()
    }

    // Press 'Escape' to safely exit fullscreen
    Shortcut {
        sequence: "Esc"
        onActivated: mainWindow.showNormal()
    }

    // Helper function to handle the logic
    function toggleFullscreen() {
        if (mainWindow.visibility === Window.FullScreen) {
            mainWindow.showNormal();
        } else {
            mainWindow.showFullScreen();
        }
    }

    // Global mouse tracker that ignores clicks, letting them pass to the UI
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton

        onPositionChanged: {
            cursorVisible = true;
            controlBar.opacity = 1.0;
            hideTimer.restart();
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: false
        cursorShape: cursorVisible ? Qt.ArrowCursor : Qt.BlankCursor

    }

    // Countdown clock
    Timer {
        id: hideTimer
        interval: 3000
        running: true // start counting immediatly
        onTriggered: {
            // Only hide if video isn't paused
            if (!videoPlayer.isPaused) {
                controlBar.opacity = 0.0;
                cursorVisible = false;
            }
        }
    }

    // VIDEO BACKEND
    MpvVideo {
        id: videoPlayer
        anchors.fill: parent

        // Custom properties to store the data coming from C++
        property double currentTime: 0
        property double totalDuration: 0
        property bool isPaused: false

        onReady: {
            videoPlayer.command(["loadfile", "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"]);
        }

        // Catch the C++ telemetry signals
        onTimeChanged: time => {
            currentTime = time;
            // Only update the slider automatically if the user isn't currently dragging it
            if (!seekSlider.pressed) {
                seekSlider.value = time;
            }
        }

        onDurationChanged: duration => {
            totalDuration = duration;
            seekSlider.to = duration; // Tell the slider how long the movie is
        }

        TapHandler {
            onTapped: {
                videoPlayer.isPaused = !videoPlayer.isPaused;
                videoPlayer.setProperty("pause", videoPlayer.isPaused ? "yes" : "no");

                // Keep the bar visible if we just paused it!
                if (videoPlayer.isPaused) {
                    controlBar.opacity = 1.0;
                    hideTimer.stop();
                } else {
                    hideTimer.restart();
                }
            }
        }
    }

    // UI OVERLAY
    Rectangle {
        id: controlBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60
        color: "#CC000000" // Semi-transparent black background

        opacity: 1.0 // Start fully visible

        // make fade smooth
        Behavior on opacity {
            NumberAnimation {
                duration: 150
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 15

            // Play / Pause Button
            Button {
                text: videoPlayer.isPaused ? "Play" : "Pause"
                onClicked: {
                    videoPlayer.isPaused = !videoPlayer.isPaused;
                    // Send the command directly to the C++ mpv engine
                    videoPlayer.setProperty("pause", videoPlayer.isPaused ? "yes" : "no");
                }
            }

            // Current Time Text
            Text {
                text: formatTime(videoPlayer.currentTime)
                color: "white"
                font.pixelSize: 16
            }

            // The Seek Bar
            Slider {
                id: seekSlider
                Layout.fillWidth: true
                from: 0

                // When the user drags the slider and lets go, jump to that part of the movie
                onMoved: {
                    // "absolute" tells mpv to jump to an exact second, rather than skipping forward 10s
                    videoPlayer.command(["seek", seekSlider.value, "absolute"]);
                }
            }

            // Total Duration Text
            Text {
                text: formatTime(videoPlayer.totalDuration)
                color: "white"
                font.pixelSize: 16
            }

            Button {
                icon.name: "fullscreen"
                icon.source: "fullscreen.svg"
                onClicked: {
                    toggleFullscreen()
                }
            }
        }
    }
}
