import QtQuick
import QtQuick.Window

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
}
