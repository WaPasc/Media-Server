import QtQuick
import QtQuick.Window
import QtQuick.Controls

Window {
    id: mainWindow
    width: 1280
    height: 720
    visible: true
    title: "Pop!_OS Media Player"
    color: "black"

    property string currentScreen: "library"

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
        onActivated: {
            mainWindow.showNormal();
            library.forceActiveFocus();
        }
    }

    Button {
            id: settingsButton
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 20
            width: 40
            height: 40
            visible: currentScreen === "library" // Only show on the main library page
            z: 100 // Ensure it sits on top

            background: Rectangle {
                color: settingsButton.hovered ? "#333333" : "transparent"
                radius: 20
            }

            icon.source: "settings.svg"
            icon.color: "#EAEAEA" // Make the SVG match our text color
            icon.width: 24
            icon.height: 24

            onClicked: currentScreen = "settings"
        }

    LibraryScreen {
        id: library
        anchors.fill: parent
        visible: currentScreen === "library"

        // Catch the signal from LibraryScreen.qml
        onMovieSelected: movieId => {
            movieDetail.movieId = movieId;
            currentScreen = "movieDetail";
        }

        onShowSelected: showId => {
            showDetail.showId = showId; // Pass ID to details screen
            currentScreen = "showDetail"; // Swap screens
        }

        onResumeMedia: (streamUrl, fileId) => {
            player.playVideo(streamUrl, fileId);
            currentScreen = "player";
        }
    }

    MovieDetailScreen {
        id: movieDetail
        anchors.fill: parent
        visible: currentScreen === "movieDetail"

        onBackClicked: currentScreen = "library"

        onMoviePlay: (streamUrl, fileId) => {
            player.playVideo(streamUrl, fileId);
            currentScreen = "player";
        }
    }

    ShowDetailScreen {
        id: showDetail
        anchors.fill: parent
        visible: currentScreen === "showDetail"

        onBackClicked: {
            currentScreen = "library";
        }

        onEpisodePlay: (streamUrl, fileId) => {
            player.playVideo(streamUrl, fileId);
            currentScreen = "player";
        }
    }

    PlayerScreen {
        id: player
        anchors.fill: parent
        visible: currentScreen === "player"

        onBackClicked: {
            // if we were watching a show, go back to the episode list
            if (showDetail.showId !== -1 && showDetail.visible === false) {
                currentScreen = "showDetail";
            } else {
                currentScreen = "library";
            }

            if (mainWindow.visibility === Window.FullScreen) {
                mainWindow.visibility = preFullscreenState;
            }
        }
        onFullscreenRequested: {
            toggleFullscreen();
        }
    }

    SettingsScreen {
        id: settingsScreen
        anchors.fill: parent
        visible: currentScreen === "settings"

        onBackClicked: {
            currentScreen = "library"
        }
    }
}
