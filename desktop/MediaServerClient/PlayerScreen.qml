import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import MediaServerClient

Item {
    id: root
    focus: true

    // Signals to talk to Main.qml
    signal backClicked
    signal fullscreenRequested

    property bool cursorVisible: true
    property int currentFileId: -1

    property double currentVolume: 100.0
    property bool isMuted: false

    // Force the player to steal keyboard focus whenever it opens
    onVisibleChanged: {
        if (visible) {
            root.forceActiveFocus();
        }
    }

    // KEYBOARD SHORTCUTS

    // Add 'event' to the parameter list so we can accept the keystroke
    Keys.onSpacePressed: event => {
        videoPlayer.isPaused = !videoPlayer.isPaused;
        videoPlayer.setProperty("pause", videoPlayer.isPaused ? "yes" : "no");

        if (videoPlayer.isPaused) {
            controlBar.opacity = 1.0;
            hideTimer.stop();
            cursorVisible = true;
        } else {
            hideTimer.restart();
        }

        // Tell Qt "I handled this keypress, do not pass it to any other buttons"
        event.accepted = true;
    }

    Keys.onUpPressed: event => {
        root.currentVolume = Math.min(100, root.currentVolume + 5);
        videoPlayer.setProperty("volume", root.currentVolume);
        if (root.isMuted) {
            root.isMuted = false;
            videoPlayer.setProperty("mute", "no");
        }
        showControls();
        event.accepted = true;
    }

    Keys.onDownPressed: event => {
        root.currentVolume = Math.max(0, root.currentVolume - 5);
        videoPlayer.setProperty("volume", root.currentVolume);
        showControls();
        event.accepted = true;
    }

    Keys.onPressed: event => {
        if (event.key === Qt.Key_M) {
            root.isMuted = !root.isMuted;
            videoPlayer.setProperty("mute", root.isMuted ? "yes" : "no");
            showControls();
            event.accepted = true;
        }
    }

    function showControls() {
        controlBar.opacity = 1.0;
        cursorVisible = true;
        hideTimer.restart();
    }

    // Public functions to control the player from the outside
    function playVideo(url, fileId) {
        root.currentFileId = fileId;

        // Ask server if we need to seek to where we left
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "http://127.0.0.1:8000/api/progress/" + fileId);
        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                let data = JSON.parse(xhr.responseText);
                let startTime = data.stopped_at;

                // Tell mpv to load the file, but pass the "start=X" option!
                if (startTime > 0) {
                    videoPlayer.command(["loadfile", url, "replace", "start=" + startTime]);
                } else {
                    videoPlayer.command(["loadfile", url]);
                }
            }
        };
        xhr.send();
    }

    function stopVideo() {
        sendProgressUpdate();
        videoPlayer.command(["stop"]);
        root.currentFileId = -1;
    }

    Timer {
        id: telemetryTimer
        interval: 5000 // 5 seconds
        running: root.visible && !videoPlayer.isPaused && root.currentFileId !== -1
        repeat: true
        onTriggered: {
            sendProgressUpdate();
        }
    }

    function sendProgressUpdate() {
        // Don't send updates if the video hasn't loaded properly
        if (videoPlayer.totalDuration <= 0)
            return;

        var xhr = new XMLHttpRequest();
        xhr.open("POST", "http://127.0.0.1:8000/api/progress");
        xhr.setRequestHeader("Content-Type", "application/json");

        var payload = {
            "file_id": root.currentFileId,
            "current_time": videoPlayer.currentTime,
            "total_duration": videoPlayer.totalDuration
        };

        xhr.send(JSON.stringify(payload));
    }

    function formatTime(timeInSeconds) {
        if (isNaN(timeInSeconds) || timeInSeconds < 0)
            return "00:00";
        let h = Math.floor(timeInSeconds / 3600);
        let m = Math.floor((timeInSeconds % 3600) / 60);
        let s = Math.floor(timeInSeconds % 60);
        let mStr = (m < 10 ? "0" : "") + m;
        let sStr = (s < 10 ? "0" : "") + s;
        return (h > 0) ? (h + ":" + mStr + ":" + sStr) : (mStr + ":" + sStr);
    }

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

    Timer {
        id: hideTimer
        interval: 3000
        running: root.visible
        onTriggered: {
            if (!videoPlayer.isPaused) {
                controlBar.opacity = 0.0;
                cursorVisible = false;
            }
        }
    }

    MpvVideo {
        id: videoPlayer
        anchors.fill: parent
        property double currentTime: 0
        property double totalDuration: 0
        property bool isPaused: false

        onTimeChanged: time => {
            currentTime = time;
            if (!seekSlider.pressed)
                seekSlider.value = time;
        }

        onDurationChanged: duration => {
            totalDuration = duration;
            seekSlider.to = duration;
        }

        TapHandler {
            onTapped: {
                videoPlayer.isPaused = !videoPlayer.isPaused;
                videoPlayer.setProperty("pause", videoPlayer.isPaused ? "yes" : "no");
                if (videoPlayer.isPaused) {
                    controlBar.opacity = 1.0;
                    hideTimer.stop();
                    cursorVisible = true;
                } else {
                    hideTimer.restart();
                }
            }
            onDoubleTapped: root.fullscreenRequested()
        }
    }

    Rectangle {
        id: controlBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60
        color: Theme.bgOverlay
        opacity: 1.0

        Behavior on opacity {
            NumberAnimation {
                duration: 150
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 15
            spacing: 15

            Button {
                text: "← Back"
                onClicked: {
                    root.stopVideo();
                    root.backClicked(); // Tell Main.qml we want to go back!
                }
            }

            Button {
                text: videoPlayer.isPaused ? "Play" : "Pause"
                onClicked: {
                    videoPlayer.isPaused = !videoPlayer.isPaused;
                    videoPlayer.setProperty("pause", videoPlayer.isPaused ? "yes" : "no");
                }
            }

            Text {
                text: formatTime(videoPlayer.currentTime)
                color: Theme.textTitle
                font.pixelSize: 16
            }

            Slider {
                id: seekSlider
                Layout.fillWidth: true
                from: 0
                onMoved: videoPlayer.command(["seek", seekSlider.value, "absolute"])
            }

            Text {
                text: formatTime(videoPlayer.totalDuration)
                color: Theme.textTitle
                font.pixelSize: 16
            }

            Button {
                icon.name: root.isMuted || root.currentVolume === 0 ? "volume-mute" : "volume-up"
                icon.source: root.isMuted || root.currentVolume === 0 ? "volume-mute.svg" : "volume-up.svg"
                onClicked: {
                    root.isMuted = !root.isMuted;
                    videoPlayer.setProperty("mute", root.isMuted ? "yes" : "no");
                }
            }

            Slider {
                id: volumeSlider
                Layout.preferredWidth: 100 // Smaller than the seek slider
                from: 0
                to: 100
                value: root.currentVolume
                onMoved: {
                    root.currentVolume = value;
                    // Auto-unmute if the user drags the slider up while muted
                    if (root.isMuted && value > 0) {
                        root.isMuted = false;
                        videoPlayer.setProperty("mute", "no");
                    }
                    videoPlayer.setProperty("volume", root.currentVolume);
                }
            }

            Button {
                text: "CC"
                font.bold: true
                palette.buttonText: Theme.textTitle
                background: Rectangle {
                    color: "transparent"
                    border.color: parent.hovered ? Theme.accent : "transparent"
                    radius: 6
                }
                onClicked: {
                    // This tells mpv to switch to the next subtitle track, or turn them off
                    videoPlayer.command(["cycle", "sub"]);

                    // Optional: Show a quick on-screen message so the user knows it changed
                    videoPlayer.command(["show-text", "Subtitles cycled"]);
                }
            }

            Button {
                icon.name: "fullscreen"
                icon.source: "fullscreen.svg"
                onClicked: root.fullscreenRequested()
            }
        }
    }
}
