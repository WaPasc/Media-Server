import QtQuick
import QtQuick.Window

Window {
    id: mainWindow
    width: 1280
    height: 720
    visible: true
    title: "Pop!_OS Media Player"
    color: "black"

    property bool isPlayingMedia: false

    function toggleFullscreen() {
        if (mainWindow.visibility === Window.FullScreen) {
            mainWindow.showNormal();
        } else {
            mainWindow.showFullScreen();
        }
    }

    Shortcut {
        sequence: "F"
        onActivated: toggleFullscreen()
    }
    Shortcut {
        sequence: "Esc"
        onActivated: mainWindow.showNormal()
    }

    LibraryScreen {
        id: library
        anchors.fill: parent
        visible: !isPlayingMedia

        // Catch the signal from LibraryScreen.qml
        onMovieSelected: streamUrl => {
            player.playVideo(streamUrl);
            isPlayingMedia = true;
        }
    }

    PlayerScreen {
        id: player
        anchors.fill: parent
        visible: isPlayingMedia

        // Catch the signals from PlayerScreen.qml
        onBackClicked: {
            isPlayingMedia = false;
            mainWindow.showNormal();
        }
        onFullscreenRequested: {
            toggleFullscreen();
        }
    }
}
