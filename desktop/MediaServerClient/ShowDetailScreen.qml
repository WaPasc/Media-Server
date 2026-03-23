import QtQuick
import QtQuick.Controls

Item {
    id: root

    signal backClicked
    signal episodeSelected(string streamUrl)

    property int showId: -1
    property string showTitle: ""
    property string backdropUrl: ""
    property string overview: ""
    property var rawShowData: null

    ListModel {
        id: seasonModel
    }
    ListModel {
        id: episodeModel
    }

    onShowIdChanged: {
        if (showId !== -1)
            loadShowDetails();
    }

    function loadShowDetails() {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "http://127.0.0.1:8000/api/show/" + showId);

        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                rawShowData = JSON.parse(xhr.responseText);
                showTitle = rawShowData.title;
                backdropUrl = rawShowData.backdrop_url || "";
                overview = rawShowData.overview || "No overview available for this show.";

                seasonModel.clear();
                let seasons = rawShowData.seasons.sort((a, b) => a.season_number - b.season_number);

                for (let s = 0; s < seasons.length; s++) {
                    seasonModel.append({
                        "seasonText": "Season " + seasons[s].season_number,
                        "seasonIndex": s
                    });
                }

                if (seasons.length > 0) {
                    seasonComboBox.currentIndex = 0;
                    loadEpisodesForSeason(0);
                }
            }
        };
        xhr.send();
    }

    function loadEpisodesForSeason(index) {
        episodeModel.clear();
        if (!rawShowData || index < 0 || index >= rawShowData.seasons.length)
            return;

        let season = rawShowData.seasons[index];
        let eps = season.episodes.sort((a, b) => a.episode_number - b.episode_number);

        for (let e = 0; e < eps.length; e++) {
            let ep = eps[e];
            episodeModel.append({
                "episodeNum": ep.episode_number,
                "epTitle": ep.title,
                "epOverview": ep.overview || "No description available.",
                "fileId": ep.file_id || -1,
                "stillUrl": ep.still_url || backdropUrl || ""
            });
        }
    }

    // STATIC BACKGROUND
    Rectangle {
        anchors.fill: parent
        color: "#09090B"

        Image {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: parent.height * 0.55 // 55vh
            source: backdropUrl
            fillMode: Image.PreserveAspectCrop
            opacity: 0.25
        }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: parent.height * 0.55
            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: "transparent"
                }
                GradientStop {
                    position: 0.75
                    color: "#BF09090B"
                }
                GradientStop {
                    position: 1.0
                    color: "#09090B"
                }
            }
        }
    }

    // --- MAIN SCROLLING CONTENT ---
    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(parent.width - 96, 1280) // max-w-7xl with 48px margins (px-12)

            // Top spacing (pt-[22vh])
            Item {
                width: 1
                height: root.height * 0.22
            }

            // Back Button
            Button {
                text: "← Back to Library"
                font.pixelSize: 16
                palette.buttonText: "#D4D4D8"
                background: Item {}
                onClicked: root.backClicked()
                contentItem: Text {
                    text: parent.text
                    color: parent.hovered ? "white" : "#D4D4D8"
                    font: parent.font
                }
            }

            Item {
                width: 1
                height: 32
            } // Margin (mb-8)

            // Title & Overview
            Text {
                text: showTitle
                color: "white"
                font.pixelSize: 56
                font.bold: true
                width: parent.width
                wrapMode: Text.WordWrap
            }

            Item {
                width: 1
                height: 12
            } // Margin (mb-3)

            Text {
                text: overview
                color: "#D4D4D8"
                font.pixelSize: 18
                width: Math.min(parent.width, 800) // max-w-3xl
                wrapMode: Text.WordWrap
                lineHeight: 1.4
            }

            Item {
                width: 1
                height: 40
            } // Margin (mb-10)

            // Season Selector Bar
            Rectangle {
                width: parent.width
                height: 80
                color: "#1A09090B"
                border.color: "#1AFFFFFF"
                radius: 12

                Column {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.margins: 16
                    spacing: 4

                    Text {
                        text: "SEASON"
                        color: "#9CA3AF"
                        font.pixelSize: 12
                        font.bold: true
                        font.letterSpacing: 1
                    }
                    ComboBox {
                        id: seasonComboBox
                        model: seasonModel
                        textRole: "seasonText"
                        width: 280
                        background: Rectangle {
                            color: "#09090B"
                            border.color: "#3F3F46"
                            radius: 8
                        }
                        contentItem: Text {
                            text: seasonComboBox.currentText
                            color: "white"
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 12
                        }
                        onCurrentIndexChanged: {
                            if (currentIndex >= 0 && seasonModel.count > 0) {
                                loadEpisodesForSeason(seasonModel.get(currentIndex).seasonIndex);
                            }
                        }
                    }
                }

                Text {
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 16
                    text: episodeModel.count + " episode" + (episodeModel.count === 1 ? "" : "s")
                    color: "#9CA3AF"
                    font.pixelSize: 14
                }
            }

            Item {
                width: 1
                height: 24
            } // Spacing before grid

            // Episode Flow Grid
            Flow {
                id: episodeFlow
                width: parent.width
                spacing: 16

                Repeater {
                    model: episodeModel

                    //FLATTENED EPISODE CARD
                    Rectangle {
                        // Responsive logic: 1 col on small screens, 2 cols on large (minus the 16px gap)
                        width: episodeFlow.width < 900 ? episodeFlow.width : (episodeFlow.width - 16) / 2
                        height: 120
                        radius: 12
                        color: mouseArea.containsMouse ? "#1A1A1A" : "#000000"
                        border.color: mouseArea.containsMouse ? "#6366F1" : "#27272A"
                        opacity: model.fileId !== -1 ? 1.0 : 0.6

                        // Thumbnail container (anchored flatly to the left)
                        Rectangle {
                            id: thumbContainer
                            anchors {
                                left: parent.left
                                top: parent.top
                                bottom: parent.bottom
                                margins: 12
                            }
                            width: 144
                            radius: 8
                            color: "#27272A"
                            clip: true
                            Image {
                                anchors.fill: parent
                                source: model.stillUrl
                                fillMode: Image.PreserveAspectCrop
                            }
                        }

                        // Text column (anchored flatly next to the thumbnail)
                        Column {
                            anchors {
                                left: thumbContainer.right
                                right: parent.right
                                top: parent.top
                                bottom: parent.bottom
                                leftMargin: 16
                                topMargin: 12
                                rightMargin: 12
                            }
                            spacing: 4

                            Row {
                                spacing: 8
                                Text {
                                    text: "Episode " + model.episodeNum
                                    color: "#818CF8"
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                                Rectangle {
                                    visible: model.fileId === -1
                                    width: 80
                                    height: 18
                                    radius: 9
                                    color: "#27272A"
                                    Text {
                                        anchors.centerIn: parent
                                        text: "MISSING FILE"
                                        color: "#9CA3AF"
                                        font.pixelSize: 9
                                        font.bold: true
                                    }
                                }
                            }

                            Text {
                                text: model.epTitle
                                color: "white"
                                font.pixelSize: 16
                                font.bold: true
                                width: parent.width
                                elide: Text.ElideRight
                            }
                            Text {
                                text: model.epOverview
                                color: "#9CA3AF"
                                font.pixelSize: 12
                                width: parent.width
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                                lineHeight: 1.2
                            }
                        }

                        MouseArea {
                            id: mouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: model.fileId !== -1 ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: {
                                if (model.fileId !== -1) {
                                    let streamUrl = "http://127.0.0.1:8000/api/stream/" + model.fileId + "?direct_play=true";
                                    root.episodeSelected(streamUrl);
                                }
                            }
                        }
                    }
                }
            }

            Item {
                width: 1
                height: 60
            } // Bottom padding
        }
    }
}
