import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import MediaServerClient

Item {
    id: root

    signal movieSelected(int movieId)
    signal showSelected(int showId)
    signal resumeMedia(string streamUrl, int fileId)

    property string currentMode: "movies"
    property string searchQuery: ""
    property var rawMediaData: [] // Stores the unfiltered JSON

    ListModel {
        id: mediaModel
    }

    // CONTINUE WATCHING DATA
    ListModel {
        id: continueWatchingModel
    }

    function fetchContinueWatching() {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "http://127.0.0.1:8000/api/continue-watching");

        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                let data = JSON.parse(xhr.responseText);
                continueWatchingModel.clear();

                for (let i = 0; i < data.length; i++) {
                    let item = data[i];

                    // Safely extract the data based on the type of media
                    let isMovie = item.type === "movie";

                    let parsedMediaId = isMovie ? item.movie.id : item.show.id;
                    let parsedTitle = isMovie ? item.movie.title : item.episode.title;
                    let parsedShowTitle = isMovie ? "" : item.show.title;

                    // Prefer Episode Still -> Movie/Show Backdrop -> Poster
                    let parsedImage = "";
                    if (isMovie) {
                        parsedImage = item.movie.backdrop_url || item.movie.poster_url || "";
                    } else {
                        parsedImage = item.episode.still_url || item.show.backdrop_url || item.show.poster_url || "";
                    }

                    continueWatchingModel.append({
                        "type": item.type,
                        "mediaId": parsedMediaId,
                        "title": parsedTitle,
                        "showTitle": parsedShowTitle,
                        "imageUrl": parsedImage,
                        "progress": item.progress_percentage || 0.0,
                        "fileId": item.file_id
                    });
                }
            }
        };
        xhr.send();
    }

    Component.onCompleted: {
        fetchMedia();
        fetchContinueWatching();
    }

    onVisibleChanged: {
        if (visible) {
            fetchMedia();
            fetchContinueWatching();
        }
    }

    function fetchMedia() {
        var xhr = new XMLHttpRequest();
        let endpoint = (currentMode === "movies") ? "/api/movies" : "/api/shows";
        xhr.open("GET", "http://127.0.0.1:8000" + endpoint);

        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                rawMediaData = JSON.parse(xhr.responseText);
                applyFilter();
            }
        };
        xhr.send();
    }

    // SEARCH FILTER LOGIC
    function applyFilter() {
        mediaModel.clear();
        let query = searchQuery.toLowerCase();

        for (let i = 0; i < rawMediaData.length; i++) {
            let item = rawMediaData[i];

            // Apply search query
            if (query === "" || item.title.toLowerCase().includes(query)) {
                mediaModel.append({
                    "mediaId": item.id,
                    "title": item.title,
                    "posterUrl": item.poster_url || "",
                    "fileId": item.file_id || 0,
                    "year": item.year ? item.year.toString() : "Unknown Year",
                    "isCompleted": item.is_completed || false,
                    "isAvailable": item.is_available !== undefined ? item.is_available : true // Add the new flag
                });
            }
        }
    }

    // BACKGROUND
    Rectangle {
        anchors.fill: parent
        color: Theme.bgBase

        // Catch clicks on empty space to unfocus search bar
        MouseArea {
            anchors.fill: parent
            onClicked: root.forceActiveFocus()
        }
    }

    // NAVBAR
    Rectangle {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 70
        color: Theme.bgBase
        z: 20 // Keep above the grid

        Row {
            anchors.fill: parent
            anchors.leftMargin: 48
            spacing: 30

            Text {
                text: "MEDIA"
                color: Theme.textTitle
                font.pixelSize: 22
                font.bold: true
                font.letterSpacing: 2
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Movies"
                font.pixelSize: 16
                font.bold: currentMode === "movies"
                color: currentMode === "movies" ? Theme.textTitle : (moviesTabMouse.containsMouse ? Theme.textHover : Theme.textSecondary)
                anchors.verticalCenter: parent.verticalCenter
                MouseArea {
                    id: moviesTabMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        currentMode = "movies";
                        fetchMedia();
                    }
                }
            }

            Text {
                text: "TV Shows"
                font.pixelSize: 16
                font.bold: currentMode === "shows"
                color: currentMode === "shows" ? Theme.textTitle : (showsTabMouse.containsMouse ? Theme.textHover : Theme.textSecondary)
                anchors.verticalCenter: parent.verticalCenter
                MouseArea {
                    id: showsTabMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        currentMode = "shows";
                        fetchMedia();
                    }
                }
            }
        }
    }

    // SEARCH INPUT
    TextField {
        id: searchField
        anchors.top: topBar.bottom
        anchors.left: parent.left
        anchors.leftMargin: 48
        anchors.topMargin: 10
        width: Math.min(parent.width - 96, 448)
        height: 48

        placeholderText: "Search " + currentMode + "..."
        placeholderTextColor: Theme.textSecondary
        color: Theme.textTitle
        font.pixelSize: 16

        leftPadding: 20
        rightPadding: 20

        background: Rectangle {
            color: Theme.bgCard
            border.color: searchField.activeFocus ? Theme.accent : Theme.borderMain
            border.width: 1
            radius: 12
        }

        onTextChanged: {
            root.searchQuery = text;
            root.applyFilter();
        }
    }

    // MEDIA GRID
    GridView {
        anchors.top: searchField.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 48
        anchors.topMargin: 32

        TapHandler {
            onTapped: root.forceActiveFocus()
        }

        header: Column {
            width: GridView.view.width
            spacing: 16
            // Only show this entire section if there is actually data
            visible: continueWatchingModel.count > 0

            // Give it some bottom margin so it doesn't crowd the main grid
            bottomPadding: 32

            Text {
                text: "Continue Watching"
                color: Theme.textTitle
                font.pixelSize: 22
                font.bold: true
                font.letterSpacing: 1
            }

            ListView {
                width: parent.width
                height: 190 // 140 for image + 50 for text
                orientation: ListView.Horizontal
                spacing: 12
                model: continueWatchingModel

                interactive: true
                delegate: LandscapeCard {
                    width: 250
                    height: 190
                    fileId: model.fileId
                    imageUrl: model.imageUrl
                    mainTitle: model.type === "episode" ? model.showTitle : model.title
                    subTitle: model.type === "episode" ? model.title : (model.progress + "% Complete")

                    showProgressBar: true
                    progress: model.progress

                    onClicked: id => {
                        let streamUrl = "http://127.0.0.1:8000/api/stream/" + id + "?direct_play=true";
                        root.resumeMedia(streamUrl, id);
                    }
                }
            }
        }

        model: mediaModel
        cellWidth: 220
        cellHeight: 380
        clip: true

        // Posters
        delegate: MediaCard {
            mediaId: model.mediaId
            title: model.title
            year: model.year
            posterUrl: model.posterUrl
            isAvailable: model.isAvailable
            isCompleted: model.isCompleted
            showCheckmark: currentMode === "movies"

            onClicked: id => {
                if (currentMode === "movies") {
                    root.movieSelected(id);
                } else {
                    root.showSelected(id);
                }
            }
        }
    }
}
