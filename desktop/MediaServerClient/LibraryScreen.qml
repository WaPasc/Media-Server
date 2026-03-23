import QtQuick
import QtQuick.Controls

Item {
    id: root

    // This signal acts as our outbound "event"
    signal movieSelected(string streamUrl)

    ListModel {
        id: videoModel
    }

    Component.onCompleted: fetchVideosFromBackend()

    function fetchVideosFromBackend() {
        videoModel.clear();
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "http://127.0.0.1:8000/api/movies");
        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                let movies = JSON.parse(xhr.responseText);
                for (let i = 0; i < movies.length; i++) {
                    if (movies[i].file_id !== null) {
                        videoModel.append({
                            "title": movies[i].title,
                            "posterUrl": movies[i].poster_url || "",
                            "fileId": movies[i].file_id,
                            "year": movies[i].year
                        });
                    }
                }
            }
        };
        xhr.send();
    }

    GridView {
        anchors.fill: parent
        anchors.margins: 40
        model: videoModel
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
                    let streamUrl = "http://127.0.0.1:8000/api/stream/" + model.fileId + "?direct_play=true";
                    // Emit the signal, passing the URL out of this component!
                    root.movieSelected(streamUrl);
                }
            }
        }
    }
}
