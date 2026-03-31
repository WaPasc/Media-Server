import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import MediaServerClient

Item {
    id: root

    signal backClicked
    signal mediaPlay(string streamUrl, int fileId)

    ListModel {
        id: historyModel
    }

    Component.onCompleted: {
        fetchHistory();
    }

    onVisibleChanged: {
        if (visible) {
            fetchHistory();
        }
    }

    function fetchHistory() {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "http://127.0.0.1:8000/api/history");
        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                let data = JSON.parse(xhr.responseText);
                historyModel.clear();

                for (let i = 0; i < data.length; i++) {
                    let item = data[i];
                    let isMovie = item.type === "movie";
                    let parsedTitle = isMovie ? item.movie.title : item.episode.title;
                    let parsedShowTitle = isMovie ? "" : item.show.title;

                    // Prefer Episode Still -> Movie/Show Backdrop -> Poster
                    let parsedImage = "";
                    if (isMovie) {
                        parsedImage = item.movie.backdrop_url || item.movie.poster_url || "";
                    } else {
                        parsedImage = item.episode.still_url || item.show.backdrop_url || item.show.poster_url || "";
                    }

                    historyModel.append({
                        "type": item.type,
                        "title": parsedTitle,
                        "showTitle": parsedShowTitle,
                        "imageUrl": parsedImage,
                        "fileId": item.file_id,
                        // Optional: If you want to show when they watched it
                        "watchedDate": item.last_watched || "Previously Watched"
                    });
                }
            }
        };
        xhr.send();
    }

    // BACKGROUND
    Rectangle {
        anchors.fill: parent
        color: Theme.bgBase
    }

    // NAVBAR
    Rectangle {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 70
        color: Theme.bgBase
        z: 20

        Row {
            anchors.fill: parent
            anchors.leftMargin: 48
            spacing: 20

            // BACK BUTTON
            Button {
                id: backButton
                anchors.verticalCenter: parent.verticalCenter
                width: 40
                height: 40

                background: Rectangle {
                    color: backButton.hovered ? Theme.bgCardHover : "transparent"
                    radius: 20
                }

                icon.source: "back.svg"
                icon.color: Theme.iconColor
                icon.width: 24
                icon.height: 24

                onClicked: root.backClicked()
            }

            Text {
                text: "WATCH HISTORY"
                color: Theme.textTitle
                font.pixelSize: 22
                font.bold: true
                font.letterSpacing: 2
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    // HISTORY GRID
    GridView {
        id: historyGrid
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 48
        anchors.topMargin: 20

        model: historyModel

        // Wide 16:9 cards
        cellWidth: 300
        cellHeight: 260
        clip: true

        delegate: Item {
            width: GridView.view.cellWidth
            height: GridView.view.cellHeight

            z: mouseArea.containsMouse ? 10 : 0

            Column {
                anchors.centerIn: parent
                width: 260
                spacing: 12

                scale: mouseArea.containsMouse ? 1.05 : 1.0
                Behavior on scale {
                    NumberAnimation {
                        duration: 200
                        easing.type: Easing.OutQuart
                    }
                }

                // THUMBNAIL CONTAINER
                Item {
                    width: 260
                    height: 146 // 16:9 aspect ratio

                    Rectangle {
                        anchors.fill: parent
                        radius: 12
                        color: Theme.bgCard
                    }

                    Item {
                        id: contentToMask
                        anchors.fill: parent
                        anchors.margins: 1
                        visible: false
                        layer.enabled: true

                        Image {
                            anchors.fill: parent
                            source: model.imageUrl
                            fillMode: Image.PreserveAspectCrop
                        }

                        // Play button overlay on hover
                        Rectangle {
                            anchors.fill: parent
                            color: Theme.bgOverlayLight
                            opacity: mouseArea.containsMouse ? 1.0 : 0.0
                            Behavior on opacity {
                                NumberAnimation {
                                    duration: 150
                                }
                            }
                        }
                    }

                    Item {
                        id: imageMask
                        anchors.fill: contentToMask
                        layer.enabled: true
                        visible: false

                        Rectangle {
                            anchors.fill: parent
                            radius: 11
                            color: "black"
                        }
                    }

                    MultiEffect {
                        anchors.fill: contentToMask
                        source: contentToMask
                        maskEnabled: true
                        maskSource: imageMask
                    }

                    Rectangle {
                        anchors.fill: parent
                        color: "transparent"
                        radius: 12
                        border.width: 1
                        border.color: mouseArea.containsMouse ? Theme.borderHover : Theme.borderMain
                    }
                }

                // TEXT INFO
                Column {
                    width: parent.width
                    spacing: 4

                    Text {
                        text: model.type === "episode" ? model.showTitle : model.title
                        color: Theme.textPrimary
                        font.pixelSize: 16
                        font.bold: true
                        width: parent.width
                        elide: Text.ElideRight
                    }

                    Text {
                        text: model.type === "episode" ? model.title : "Movie"
                        color: Theme.textSecondary
                        font.pixelSize: 13
                        width: parent.width
                        elide: Text.ElideRight
                    }
                }
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor

                onClicked: {
                    let streamUrl = "http://127.0.0.1:8000/api/stream/" + model.fileId + "?direct_play=true";
                    root.mediaPlay(streamUrl, model.fileId);
                }
            }
        }
    }
}
