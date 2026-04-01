import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import MediaServerClient
import "NetworkManager.js" as API

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
        API.get("/api/history").then(function (data) {
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
        }).catch(function (error) {
            console.error("Failed to load history:", error);
        });
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

        // The invisible "box" the grid creates for each item
        cellWidth: 280
        cellHeight: 210
        clip: true

        // Wrap the card in a basic Item that fills the invisible box
        delegate: Item {
            width: GridView.view.cellWidth
            height: GridView.view.cellHeight

            // Center the actual visual card inside the box and give it a fixed size
            LandscapeCard {
                anchors.centerIn: parent

                // This makes the card physically smaller than the cell, creating spacing
                width: 270
                height: 200

                fileId: model.fileId
                imageUrl: model.imageUrl
                mainTitle: model.type === "episode" ? model.showTitle : model.title
                subTitle: model.type === "episode" ? model.title : "Movie"

                showProgressBar: false

                onClicked: id => {
                    let streamUrl = "http://127.0.0.1:8000/api/stream/" + id + "?direct_play=true";
                    root.mediaPlay(streamUrl, id);
                }
            }
        }
    }
}
