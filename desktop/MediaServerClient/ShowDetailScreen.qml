import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import MediaServerClient

Item {
    id: root

    signal backClicked
    signal episodePlay(string streamUrl, int fileId)

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
                "stillUrl": ep.still_url || backdropUrl || "",
                "isCompleted": ep.is_completed || false
            });
        }
    }

    // STATIC BACKGROUND
    Rectangle {
        anchors.fill: parent
        color: Theme.bgBase

        Item {
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(parent.width, 1600) // Max width for ultra-wide monitors
            height: parent.height * 0.60 // Slightly taller (60vh)

            Image {
                anchors.fill: parent
                source: backdropUrl
                fillMode: Image.PreserveAspectCrop
                verticalAlignment: Image.AlignTop // Pins the top of the image
                opacity: 0.35
            }

            // Vertical Fade (Hides the harsh bottom edge)
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop {
                        position: 0.0
                        color: "transparent"
                    }
                    GradientStop {
                        position: 0.60
                        color: Theme.bgBaseFade
                    }
                    GradientStop {
                        position: 1.0
                        color: Theme.bgBase
                    }
                }
            }

            // Horizontal Fade (Blends the left/right edges into the black background)
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop {
                        position: 0.0
                        color: Theme.bgBase
                    }
                    GradientStop {
                        position: 0.15
                        color: "transparent"
                    }
                    GradientStop {
                        position: 0.85
                        color: "transparent"
                    }
                    GradientStop {
                        position: 1.0
                        color: Theme.bgBase
                    }
                }
            }
        }
    }

    // MAIN SCROLLING CONTENT
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
                palette.buttonText: Theme.textHover
                background: Item {}
                onClicked: root.backClicked()
                contentItem: Text {
                    text: parent.text
                    color: parent.hovered ? Theme.textTitle : Theme.textHover
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
                color: Theme.textTitle
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
                color: Theme.textHover
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
                color: Theme.bgPanel
                border.color: Theme.borderLight
                radius: 12

                Column {
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.margins: 16
                    spacing: 4

                    Text {
                        text: "SEASON"
                        color: Theme.textTertiary
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
                            color: Theme.bgBase
                            border.color: Theme.borderInput
                            radius: 8
                        }
                        contentItem: Text {
                            text: seasonComboBox.currentText
                            color: Theme.textTitle
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
                    color: Theme.textTertiary
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

                    // FLATTENED EPISODE CARD
                    Rectangle {
                        // Responsive logic: 1 col on small screens, 2 cols on large (minus the 16px gap)
                        width: episodeFlow.width < 900 ? episodeFlow.width : (episodeFlow.width - 16) / 2
                        height: 120
                        radius: 12
                        color: mouseArea.containsMouse ? Theme.bgCardHover : Theme.bgBlack
                        border.color: mouseArea.containsMouse ? Theme.accent : Theme.borderDark
                        opacity: model.fileId !== -1 ? 1.0 : 0.6

                        // Thumbnail container (anchored flatly to the left)
                        Item {
                            id: thumbContainer
                            anchors {
                                left: parent.left
                                top: parent.top
                                bottom: parent.bottom
                                margins: 12
                            }
                            width: 144

                            // Solid Background (shows while loading or if image is missing)
                            Rectangle {
                                anchors.fill: parent
                                radius: 8
                                color: Theme.bgBadge
                            }

                            //The raw image (hidden)
                            Image {
                                id: stillImage
                                anchors.fill: parent
                                source: model.stillUrl
                                fillMode: Image.PreserveAspectCrop
                                visible: false
                            }

                            // The Mask (hidden)
                            Item {
                                id: imageMask
                                anchors.fill: stillImage
                                layer.enabled: true
                                visible: false

                                Rectangle {
                                    anchors.fill: parent
                                    radius: 8 // This sets the roundness of the image
                                    color: "black"
                                }
                            }

                            // The MultiEffect (Renders the rounded image)
                            MultiEffect {
                                anchors.fill: stillImage
                                source: stillImage
                                maskEnabled: true
                                maskSource: imageMask
                                visible: model.stillUrl !== ""
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
                                    color: Theme.accentLight
                                    font.pixelSize: 12
                                    font.bold: true
                                }
                                Rectangle {
                                    visible: model.fileId === -1
                                    width: 80
                                    height: 18
                                    radius: 9
                                    color: Theme.bgBadge
                                    Text {
                                        anchors.centerIn: parent
                                        text: "MISSING FILE"
                                        color: Theme.textTertiary
                                        font.pixelSize: 9
                                        font.bold: true
                                    }
                                }
                            }

                            Text {
                                text: model.epTitle
                                color: Theme.textTitle
                                font.pixelSize: 16
                                font.bold: true
                                width: parent.width
                                elide: Text.ElideRight
                            }
                            Text {
                                text: model.epOverview
                                color: Theme.textTertiary
                                font.pixelSize: 12
                                width: parent.width
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                                lineHeight: 1.2
                            }
                        }

                        Image {
                            source: "check-circle.svg"
                            width: 22
                            height: 22
                            sourceSize.width: 22
                            sourceSize.height: 22

                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 12

                            visible: model.isCompleted || false

                            Behavior on opacity {
                                NumberAnimation {
                                    duration: 200
                                }
                            }
                            opacity: visible ? 1.0 : 0.0
                        }

                        MouseArea {
                            id: mouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: model.fileId !== -1 ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: {
                                if (model.fileId !== -1) {
                                    let streamUrl = "http://127.0.0.1:8000/api/stream/" + model.fileId + "?direct_play=true";
                                    root.episodePlay(streamUrl, model.fileId);
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
