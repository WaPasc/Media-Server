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

            // Skip movies without files
            if (currentMode === "movies" && item.file_id === null)
                continue;

            // Apply search query
            if (query === "" || item.title.toLowerCase().includes(query)) {
                mediaModel.append({
                    "mediaId": item.id,
                    "title": item.title,
                    "posterUrl": item.poster_url || "",
                    "fileId": item.file_id || 0,
                    "year": item.year ? item.year.toString() : "Unknown Year"
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
                spacing: 24
                model: continueWatchingModel

                interactive: true

                delegate: Item {
                    width: 250 // 16:9 aspect ratio width
                    height: 190

                    z: cwMouseArea.containsMouse ? 10 : 0

                    // The Hover Scale Animation Container
                    Item {
                        anchors.fill: parent
                        scale: cwMouseArea.containsMouse ? 1.05 : 1.0
                        Behavior on scale {
                            NumberAnimation {
                                duration: 200
                                easing.type: Easing.OutQuart
                            }
                        }

                        // The Image Container
                        Item {
                            id: cwImageContainer
                            width: 250
                            height: 140

                            // Solid Background
                            Rectangle {
                                anchors.fill: parent
                                radius: 12
                                color: Theme.bgCard
                            }

                            // The Content to be masked (Image + Overlays)
                            Item {
                                id: contentToMask
                                anchors.fill: parent
                                anchors.margins: 1 // Keep inside the border
                                visible: false // Hidden so MultiEffect can render it
                                layer.enabled: true // Groups all children into one texture

                                Image {
                                    anchors.fill: parent
                                    source: model.imageUrl
                                    fillMode: Image.PreserveAspectCrop
                                }

                                // The Dark Overlay
                                Rectangle {
                                    anchors.bottom: parent.bottom
                                    width: parent.width
                                    height: 40
                                    gradient: Gradient {
                                        GradientStop {
                                            position: 0.0
                                            color: "transparent"
                                        }
                                        GradientStop {
                                            position: 1.0
                                            color: "#CC000000"
                                        }
                                    }
                                }

                                // The Progress Bar Track
                                Rectangle {
                                    anchors.bottom: parent.bottom
                                    width: parent.width
                                    height: 4
                                    color: "transparent"
                                }

                                // The Progress Bar Fill
                                Rectangle {
                                    anchors.bottom: parent.bottom
                                    anchors.left: parent.left
                                    width: parent.width * (model.progress / 100)
                                    height: 4
                                    color: Theme.accent
                                }
                            }

                            // The Mask
                            Item {
                                id: cwImageMask
                                anchors.fill: contentToMask
                                layer.enabled: true
                                visible: false

                                Rectangle {
                                    anchors.fill: parent
                                    radius: 11 // Inner radius
                                    color: "black"
                                }
                            }

                            // The MultiEffect (Renders everything beautifully rounded)
                            MultiEffect {
                                anchors.fill: contentToMask
                                source: contentToMask
                                maskEnabled: true
                                maskSource: cwImageMask
                            }

                            // The Border (Rendered last so it sits on top)
                            Rectangle {
                                anchors.fill: parent
                                color: "transparent"
                                radius: 12
                                border.width: 1
                                border.color: cwMouseArea.containsMouse ? Theme.borderHover : Theme.borderMain
                            }
                        }

                        // The Text Container
                        Column {
                            anchors.top: cwImageContainer.bottom
                            anchors.topMargin: 8
                            width: parent.width
                            spacing: 2

                            Text {
                                text: model.type === "episode" ? model.showTitle : model.title
                                color: Theme.textPrimary
                                font.pixelSize: 15
                                font.bold: true
                                width: parent.width
                                elide: Text.ElideRight
                            }
                            Text {
                                text: model.type === "episode" ? model.title : (model.progress + "% Complete")
                                color: Theme.textSecondary
                                font.pixelSize: 12
                                width: parent.width
                                elide: Text.ElideRight
                            }
                        }

                        // The Click Handler
                        MouseArea {
                            id: cwMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                let streamUrl = "http://127.0.0.1:8000/api/stream/" + model.fileId + "?direct_play=true";
                                root.resumeMedia(streamUrl, model.fileId);
                            }
                        }
                    }
                }
            }
        }

        model: mediaModel
        cellWidth: 220
        cellHeight: 380
        clip: true

        delegate: Item {
            width: GridView.view.cellWidth
            height: GridView.view.cellHeight

            z: mouseArea.containsMouse ? 10 : 0

            // Inner container that handles the scale animation
            Column {
                anchors.centerIn: parent
                width: 200
                spacing: 12

                scale: mouseArea.containsMouse ? 1.05 : 1.0
                Behavior on scale {
                    NumberAnimation {
                        duration: 300
                        easing.type: Easing.OutQuart
                    }
                }

                // POSTER CONTAINER
                Item {
                    width: 200
                    height: 300

                    // Solid Background
                    Rectangle {
                        anchors.fill: parent
                        radius: 12
                        color: Theme.bgCard
                    }

                    // The raw image (hidden)
                    Image {
                        id: posterImage
                        anchors.fill: parent
                        anchors.margins: 1
                        source: model.posterUrl
                        fillMode: Image.PreserveAspectCrop
                        visible: false
                    }

                    // The Mask (hidden)
                    Item {
                        id: imageMask
                        anchors.fill: posterImage // Match the shrunk size
                        layer.enabled: true
                        visible: false

                        Rectangle {
                            anchors.fill: parent
                            radius: 11 // 12px outer radius minus 1px margin = 11px
                            color: "black" // Masking color does not need theming
                        }
                    }

                    // The MultiEffect (Renders the rounded image)
                    MultiEffect {
                        anchors.fill: posterImage // Bind to the shrunk size
                        source: posterImage
                        maskEnabled: true
                        maskSource: imageMask
                        visible: model.posterUrl !== ""
                    }

                    // "No Poster" Text
                    Text {
                        anchors.centerIn: parent
                        text: "No Poster"
                        color: Theme.textMuted
                        font.pixelSize: 14
                        visible: model.posterUrl === ""
                    }

                    // The border (Rendered last so it sits on top of everything)
                    Rectangle {
                        anchors.fill: parent
                        color: "transparent"
                        radius: 12
                        border.width: 1
                        border.color: mouseArea.containsMouse ? Theme.borderHover : Theme.borderMain
                    }
                }

                // TEXT CONTAINER
                Column {
                    width: parent.width
                    spacing: 2

                    Text {
                        text: model.title
                        color: Theme.textPrimary
                        font.pixelSize: 16
                        font.bold: true
                        width: parent.width
                        elide: Text.ElideRight
                    }

                    Text {
                        text: model.year
                        color: Theme.textSecondary
                        font.pixelSize: 12
                        font.bold: true
                    }
                }
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (currentMode === "movies") {
                        // Pass the mediaId instead of constructing the stream URL
                        root.movieSelected(model.mediaId);
                    } else {
                        root.showSelected(model.mediaId);
                    }
                }
            }
        }
    }
}
