import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import MediaServerClient

Rectangle {
    id: root

    // STATE PROPERTIES (Passed in from PlayerScreen)
    property bool isPaused: false
    property double currentTime: 0
    property double totalDuration: 0
    property double currentVolume: 100.0
    property bool isMuted: false
    property bool isFullscreen: false

    // SIGNALS (Emitted out to PlayerScreen to actually execute the commands)
    signal backClicked
    signal togglePlayPause
    signal seekRequested(double position)
    signal volumeChanged(double volume)
    signal toggleMute
    signal cycleAudio
    signal cycleSubtitles
    signal addSubtitle
    signal toggleFullscreen

    height: 60
    color: Theme.bgOverlay

    // UI needs to format time
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
            icon.color: backBtn.hovered ? Theme.iconColor : Theme.iconHoverColor
            background: Rectangle {
                color: "transparent"
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.backClicked()
            }
        }

        Button {
            id: playPauseBtn
            Layout.preferredWidth: 44
            Layout.preferredHeight: 44
            hoverEnabled: true
            focusPolicy: Qt.NoFocus
            icon.source: root.isPaused ? "play.svg" : "pause.svg"
            icon.width: 22
            icon.height: 22
            icon.color: playPauseBtn.hovered ? Theme.iconColor : Theme.iconHoverColor
            background: Rectangle {
                color: "transparent"
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.togglePlayPause()
            }
        }

        Text {
            text: formatTime(root.currentTime)
            color: Theme.textTitle
            font.pixelSize: 16
        }

        Slider {
            id: seekSlider
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            from: 0
            to: root.totalDuration
            value: root.currentTime // Binds to the prop
            hoverEnabled: true
            focusPolicy: Qt.NoFocus

            background: Rectangle {
                x: seekSlider.leftPadding
                y: seekSlider.topPadding + seekSlider.availableHeight / 2 - height / 2
                implicitHeight: 4
                color: Theme.progressToComplete
                width: seekSlider.availableWidth
                height: implicitHeight
                radius: 2

                Rectangle {
                    width: seekSlider.visualPosition * parent.width
                    height: parent.height
                    color: Theme.iconColor
                    radius: 2
                }
            }

            handle: Rectangle {
                x: seekSlider.leftPadding + seekSlider.visualPosition * (seekSlider.availableWidth - width)
                y: seekSlider.topPadding + seekSlider.availableHeight / 2 - height / 2
                visible: seekSlider.pressed || seekSlider.hovered
                implicitWidth: 12
                implicitHeight: 12
                radius: 6
                color: Theme.iconColor
            }

            onMoved: root.seekRequested(value)
        }

        Text {
            text: formatTime(root.totalDuration)
            color: Theme.textTitle
            font.pixelSize: 16
        }

        Button {
            id: volBtn
            Layout.preferredWidth: 44
            Layout.preferredHeight: 44
            hoverEnabled: true
            focusPolicy: Qt.NoFocus
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
                onClicked: root.toggleMute()
            }
        }

        Slider {
            id: volumeSlider
            Layout.preferredWidth: 100
            Layout.alignment: Qt.AlignVCenter
            from: 0
            to: 100
            value: root.currentVolume
            hoverEnabled: true
            focusPolicy: Qt.NoFocus

            background: Rectangle {
                x: volumeSlider.leftPadding
                y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                implicitHeight: 4
                width: volumeSlider.availableWidth
                height: implicitHeight
                radius: 2
                color: Theme.progressToComplete

                Rectangle {
                    width: volumeSlider.visualPosition * parent.width
                    height: parent.height
                    color: volumeSlider.hovered || volumeSlider.pressed ? Theme.iconColor : Theme.iconHoverColor
                    radius: 2
                }
            }

            handle: Rectangle {
                x: volumeSlider.leftPadding + volumeSlider.visualPosition * (volumeSlider.availableWidth - width)
                y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                implicitWidth: 12
                implicitHeight: 12
                radius: 6
                color: volumeSlider.pressed || volumeSlider.hovered ? Theme.iconColor : Theme.iconHoverColor
                scale: volumeSlider.pressed || volumeSlider.hovered ? 1.2 : 1.0
            }

            onMoved: root.volumeChanged(value)
        }

        Button {
            id: audioBtn
            Layout.preferredWidth: 44
            Layout.preferredHeight: 44
            hoverEnabled: true
            focusPolicy: Qt.NoFocus

            icon.source: "audio.svg"
            icon.width: 24
            icon.height: 24

            icon.color: audioBtn.hovered ? Theme.iconColor : Theme.iconHoverColor
            background: Rectangle {
                color: "transparent"
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.cycleAudio()
            }
        }

        Button {
            id: subBtn
            Layout.preferredWidth: 44
            Layout.preferredHeight: 44
            hoverEnabled: true
            focusPolicy: Qt.NoFocus
            icon.source: "subtitles.svg"
            icon.width: 28
            icon.height: 28
            icon.color: subBtn.hovered ? Theme.iconColor : Theme.iconHoverColor
            background: Rectangle {
                color: "transparent"
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onClicked: mouse => {
                    if (mouse.button === Qt.RightButton) {
                        root.addSubtitle();
                    } else {
                        root.cycleSubtitles();
                    }
                }
            }
        }

        Button {
            id: fullBtn
            Layout.preferredWidth: 44
            Layout.preferredHeight: 44
            hoverEnabled: true
            focusPolicy: Qt.NoFocus
            icon.source: root.isFullscreen ? "fullscreen-min.svg" : "fullscreen-max.svg"
            icon.width: 22
            icon.height: 22
            icon.color: fullBtn.hovered ? Theme.iconColor : Theme.iconHoverColor
            background: Rectangle {
                color: "transparent"
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.toggleFullscreen()
            }
        }
    }
}
