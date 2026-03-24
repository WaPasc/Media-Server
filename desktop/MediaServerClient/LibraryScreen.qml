import QtQuick
import QtQuick.Controls
import QtQuick.Effects

Item {
    id: root

    signal movieSelected(string streamUrl, int fileId)
    signal showSelected(int showId)

    property string currentMode: "movies"
    property string searchQuery: ""
    property var rawMediaData: [] // Stores the unfiltered JSON

    ListModel {
        id: mediaModel
    }

    Component.onCompleted: fetchMedia()

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
                        let streamUrl = "http://127.0.0.1:8000/api/stream/" + model.fileId + "?direct_play=true";
                        root.movieSelected(streamUrl, model.fileId);
                    } else {
                        root.showSelected(model.mediaId);
                    }
                }
            }
        }
    }
}
