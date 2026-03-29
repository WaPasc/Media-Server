import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import MediaServerClient

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
                id: backBtn
                Layout.preferredWidth: 44
                Layout.preferredHeight: 44
                hoverEnabled: true
                focusPolicy: Qt.NoFocus

                icon.source: "back.svg"
                icon.width: 22
                icon.height: 22

                // Matches the hover color transition of all other buttons
                icon.color: backBtn.hovered ? Theme.iconColor : Theme.iconHoverColor

                background: Rectangle {
                    color: "transparent"
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.NoButton
                }

                onClicked: {
                    root.stopVideo();
                    root.backClicked(); // Tell Main.qml we want to go back!
                }
            }

            Button {
                id: playPauseBtn
                Layout.preferredWidth: 44
                Layout.preferredHeight: 44
                hoverEnabled: true
                focusPolicy: Qt.NoFocus

                // Dynamically swap the icon based on the player state
                icon.source: videoPlayer.isPaused ? "play.svg" : "pause.svg"

                icon.width: 22
                icon.height: 22

                icon.color: playPauseBtn.hovered ? Theme.iconColor : Theme.iconHoverColor

                background: Rectangle {
                    color: "transparent"
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.NoButton
                }

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
                Layout.alignment: Qt.AlignVCenter
                from: 0
                hoverEnabled: true
                focusPolicy: Qt.NoFocus

                // 1. CUSTOMIZE THE TRACK (Background)
                background: Rectangle {
                    x: seekSlider.leftPadding
                    y: seekSlider.topPadding + seekSlider.availableHeight / 2 - height / 2
                    implicitWidth: 200 // This is a baseline, Layout.fillWidth overrides it anyway
                    implicitHeight: 4 // Thickness of the track
                    color: Theme.progressToComplete
                    width: seekSlider.availableWidth
                    height: implicitHeight
                    radius: 2

                    // The filled portion of the track showing playback progress
                    Rectangle {
                        width: seekSlider.visualPosition * parent.width
                        height: parent.height
                        color: Theme.iconColor
                        radius: 2
                    }
                }

                // 2. CUSTOMIZE THE KNOB (Handle)
                handle: Rectangle {
                    x: seekSlider.leftPadding + seekSlider.visualPosition * (seekSlider.availableWidth - width)
                    y: seekSlider.topPadding + seekSlider.availableHeight / 2 - height / 2
                    visible: seekSlider.pressed || seekSlider.hovered
                    implicitWidth: 12
                    implicitHeight: 12
                    radius: 6 // Makes it a perfect circle
                    color: Theme.iconColor
                }

                onMoved: videoPlayer.command(["seek", seekSlider.value, "absolute"])
            }
            Text {
                text: formatTime(videoPlayer.totalDuration)
                color: Theme.textTitle
                font.pixelSize: 16
            }

            Button {
                id: volBtn
                Layout.preferredWidth: 44
                Layout.preferredHeight: 44
                hoverEnabled: true
                focusPolicy: Qt.NoFocus

                // Dynamically swap the icon based on mute state or zero volume
                icon.source: root.isMuted || root.currentVolume === 0 ? "volume-mute.svg" : "volume-up.svg"

                icon.width: 22
                icon.height: 22

                icon.color: volBtn.hovered ? Theme.iconColor : Theme.iconHoverColor

                background: Rectangle {
                    color: "transparent"
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.NoButton
                }

                onClicked: {
                    root.isMuted = !root.isMuted;
                    videoPlayer.setProperty("mute", root.isMuted ? "yes" : "no");
                }
            }

            Slider {
                id: volumeSlider
                Layout.preferredWidth: 100
                Layout.alignment: Qt.AlignVCenter // Keeps it perfectly centered with the buttons
                from: 0
                to: 100
                value: root.currentVolume
                hoverEnabled: true
                focusPolicy: Qt.NoFocus

                // CUSTOMIZE THE TRACK (Background)
                background: Rectangle {
                    x: volumeSlider.leftPadding
                    y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                    implicitWidth: 100
                    implicitHeight: 4 // Thickness of the track
                    width: volumeSlider.availableWidth
                    height: implicitHeight
                    radius: 2
                    color: Theme.progressToComplete

                    // The filled portion of the track
                    Rectangle {
                        width: volumeSlider.visualPosition * parent.width
                        height: parent.height
                        color: volumeSlider.hovered || volumeSlider.pressed ? Theme.iconColor : Theme.iconHoverColor
                        radius: 2
                    }
                }

                // CUSTOMIZE THE KNOB (Handle)
                handle: Rectangle {
                    x: volumeSlider.leftPadding + volumeSlider.visualPosition * (volumeSlider.availableWidth - width)
                    y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                    implicitWidth: 12
                    implicitHeight: 12
                    radius: 6 // Makes it a perfect circle
                    color: volumeSlider.pressed || volumeSlider.hovered ? Theme.iconColor : Theme.iconHoverColor

                    // Slightly enlarge the knob when interacting with it
                    scale: volumeSlider.pressed || volumeSlider.hovered ? 1.2 : 1.0
                }

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
                id: subBtn
                Layout.preferredWidth: 44
                Layout.preferredHeight: 44
                hoverEnabled: true // Tell the button to track hovers
                focusPolicy: Qt.NoFocus

                icon.source: "subtitles.svg"
                icon.width: 28
                icon.height: 28

                // Flipped the colors so hoverColor triggers on hover
                icon.color: subBtn.hovered ? Theme.iconColor : Theme.iconHoverColor

                background: Rectangle {
                    color: "transparent"
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.NoButton
                }

                onClicked: {
                    videoPlayer.command(["cycle", "sub"]);
                    videoPlayer.command(["show-text", "Subtitles cycled"]);
                }
            }

            Button {
                id: fullBtn
                Layout.preferredWidth: 44
                Layout.preferredHeight: 44
                hoverEnabled: true
                focusPolicy: Qt.NoFocus

                // Will dynamically change the icon if we are in fullscreen
                icon.source: root.isFullscreen ? "fullscreen-min.svg" : "fullscreen-max.svg"

                icon.width: 22
                icon.height: 22

                // Changed subBtn.hovered to fullBtn.hovered
                icon.color: fullBtn.hovered ? Theme.iconColor : Theme.iconHoverColor

                background: Rectangle {
                    color: "transparent"
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.NoButton
                }

                onClicked: root.fullscreenRequested()
            }
        }
    }
}
