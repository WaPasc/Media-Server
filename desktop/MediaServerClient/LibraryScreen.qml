import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    // This signal acts as our outbound "event"
    signal movieSelected(string streamUrl)
    signal showSelected(int showId)

    property string currentMode: "movies"

    ListModel {
        id: mediaModel
    }

    Component.onCompleted: fetchMedia()

    function fetchMedia() {
        mediaModel.clear();
        var xhr = new XMLHttpRequest();
        let endpoint = (currentMode === "movies") ? "/api/movies" : "/api/shows";
        xhr.open("GET", "http://127.0.0.1:8000" + endpoint);

        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                let data = JSON.parse(xhr.responseText);
                for (let i = 0; i < data.length; i++) {
                    // For movies, file_id must be valid. For shows, we just need the show id.
                    if (currentMode === "shows" || data[i].file_id !== null) {
                        mediaModel.append({
                            "mediaId": data[i].id,
                            "title": data[i].title,
                            "posterUrl": data[i].poster_url || "",
                            "fileId": data[i].file_id || 0,
                            "year": data[i].year || ""
                        });
                    }
                }
            }
        };
        xhr.send();
    }

    RowLayout {
        id: topBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 60
        anchors.margins: 20
        spacing: 20

        Button {
            text: "Movies"
            highlighted: currentMode === "movies"
            onClicked: {
                currentMode = "movies";
                fetchMedia();
            }
        }
        Button {
            text: "TV Shows"
            highlighted: currentMode === "shows"
            onClicked: {
                currentMode = "shows";
                fetchMedia();
            }
        }
    }

    GridView {
        anchors.top: topBar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 40
        model: mediaModel
        cellWidth: 220
        cellHeight: 330

        delegate: Rectangle {
            width: 200
            height: 300
            color: "#1E1E1E"
            radius: 8
            clip: true

            Image {
                anchors.fill: parent
                source: model.posterUrl
                fillMode: Image.PreserveAspectCrop

                Text {
                    anchors.centerIn: parent
                    anchors.margins: 10
                    width: parent.width - 20
                    text: model.title + "\n(" + model.year + ")"
                    color: "white"
                    font.pixelSize: 16
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    visible: parent.status !== Image.Ready
                }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (currentMode === "movies") {
                        let streamUrl = "http://127.0.0.1:8000/api/stream/" + model.fileId + "?direct_play=true";
                        // Emit the signal, passing the URL out of this component!
                        root.movieSelected(streamUrl);
                    } else {
                        // It's a TV Show, pass the ID
                        root.showSelected(model.mediaId);
                    }
                }
            }
        }
    }
}
