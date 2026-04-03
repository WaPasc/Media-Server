import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import MediaServerClient
import "NetworkManager.js" as API

Item {
    id: root
    focus: true

    signal backClicked
    signal fullscreenRequested

    property bool cursorVisible: true
    property int currentFileId: -1
    property double currentVolume: 100.0
    property bool isMuted: false
    property bool isFullscreen: false
    property int seekDirection: 0

    onVisibleChanged: {
        if (visible)
            root.forceActiveFocus();
    }

    function showControls() {
        controlBar.opacity = 1.0;
        cursorVisible = true;
        hideTimer.restart();
    }

    // Seek timer for hold-to-fast-seek
    Timer {
        id: fastSeekTimer
        interval: 300
        repeat: true
        onTriggered: {
            videoPlayer.command(["seek", (root.seekDirection === 1) ? "15" : "-15", "relative+exact"]);
            showControls();
        }
    }

    // Keyboard shortcuts
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
        if (event.key === Qt.Key_Right || event.key === Qt.Key_Left) {
            if (event.isAutoRepeat) {
                if (!fastSeekTimer.running)
                    fastSeekTimer.start();
            } else {
                root.seekDirection = (event.key === Qt.Key_Right) ? 1 : -1;
            }
            event.accepted = true;
            return;
        }
        if (event.key === Qt.Key_M) {
            root.isMuted = !root.isMuted;
            videoPlayer.setProperty("mute", root.isMuted ? "yes" : "no");
            showControls();
            event.accepted = true;
        }
    }

    Keys.onReleased: event => {
        if (event.key !== Qt.Key_Right && event.key !== Qt.Key_Left)
            return;
        if (event.isAutoRepeat) {
            event.accepted = true;
            return;
        }

        const wasFastSeeking = fastSeekTimer.running;
        fastSeekTimer.stop();
        if (!wasFastSeeking) {
            videoPlayer.command(["seek", (root.seekDirection === 1) ? "5" : "-5", "relative+exact"]);
            showControls();
        }
        event.accepted = true;
    }

    // Public functions to control the player from the outside
    function playVideo(url, fileId) {
        root.currentFileId = fileId;

        // Ask server if we need to seek to where we left
        API.get("/api/progress/" + fileId).then(function (data) {
            let startTime = data.stopped_at;

            // Tell mpv to load the file, but pass the "start=X" option
            if (startTime > 0) {
                videoPlayer.command(["loadfile", url, "replace", "start=" + startTime]);
            } else {
                videoPlayer.command(["loadfile", url]);
            }
        }).catch(function (error) {
            console.error("Failed to fetch progress, playing from start:", error);
            // Fallback: Just play from the beginning if the network request fails
            videoPlayer.command(["loadfile", url]);
        });
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

        var payload = {
            "file_id": root.currentFileId,
            "current_time": videoPlayer.currentTime,
            "total_duration": videoPlayer.totalDuration
        };

        API.post("/api/progress", payload).then(function (data) {}).catch(function (error) {
            console.error("Failed to update progress:", error);
        });
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

    // NATIVE FILE PICKER FOR SUBTITLES
    FileDialog {
        id: subtitleFileDialog
        title: "Select Subtitle File"

        // Only allow selecting subtitle formats
        nameFilters: ["Subtitle files (*.srt *.vtt *.ass *.sub)", "All files (*)"]

        onAccepted: {
            // Qt returns a URL
            // Cconvert it to a standard file path for mpv
            let path = selectedFile.toString();

            // Decode URL-encoded characters
            path = decodeURIComponent(path);

            // Clean up the "file://" prefix for Windows/Linux compatibility
            if (path.startsWith("file:///")) {
                // Windows leaves a slash before the drive letter (e.g., /C:/)
                if (Qt.platform.os === "windows") {
                    path = path.substring(8);
                } else {
                    path = path.substring(7);
                }
            }

            console.log("Loading subtitle:", path);

            // Tell mpv to load the external subtitle track
            videoPlayer.command(["sub-add", path]);
        }
        onRejected: {
            console.log("Subtitle selection canceled");
        }
    }

    PlayerControls {
        id: controlBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        opacity: 1.0

        // Send data in to the controls
        isPaused: videoPlayer.isPaused
        currentTime: videoPlayer.currentTime
        totalDuration: videoPlayer.totalDuration
        currentVolume: root.currentVolume
        isMuted: root.isMuted
        isFullscreen: root.isFullscreen

        Behavior on opacity {
            NumberAnimation {
                duration: 150
            }
        }

        // Handle signals coming OUT of the controls
        onBackClicked: {
            root.stopVideo();
            root.backClicked();
        }
        onTogglePlayPause: {
            videoPlayer.isPaused = !videoPlayer.isPaused;
            videoPlayer.setProperty("pause", videoPlayer.isPaused ? "yes" : "no");
        }
        onSeekRequested: position => {
            videoPlayer.command(["seek", position, "absolute"]);
        }
        onVolumeChanged: volume => {
            root.currentVolume = volume;
            if (root.isMuted && volume > 0) {
                root.isMuted = false;
                videoPlayer.setProperty("mute", "no");
            }
            videoPlayer.setProperty("volume", root.currentVolume);
        }
        onToggleMute: {
            root.isMuted = !root.isMuted;
            videoPlayer.setProperty("mute", root.isMuted ? "yes" : "no");
        }
        onCycleSubtitles: {
            videoPlayer.command(["cycle", "sub"]);
            videoPlayer.command(["show-text", "Subtitles cycled"]);
        }
        onAddSubtitle: {
            subtitleFileDialog.open();
        }
        onToggleFullscreen: {
            root.fullscreenRequested();
        }
    }
}
