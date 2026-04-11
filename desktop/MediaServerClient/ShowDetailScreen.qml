import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import MediaServerClient
import "NetworkManager.js" as API

Item {
    id: root

    signal backClicked
    signal episodePlay(string streamUrl, int fileId)

    property int showId: -1
    property string showTitle: ""
    property string backdropUrl: ""
    property string overview: ""
    property var rawShowData: null
    property int savedSeasonIndex: 0
    property var nextEpisode: null

    ListModel {
        id: seasonModel
    }
    ListModel {
        id: episodeModel
    }

    onShowIdChanged: {
        if (showId !== -1) {
            savedSeasonIndex = 0; // Reset season memory for new show
            loadShowDetails();
        }
    }
    onVisibleChanged: {
        if (visible && showId !== -1) {
            loadShowDetails();
        }
    }

    function loadShowDetails() {
        API.get("/api/show/" + showId).then(function (data) {
            rawShowData = data;
            showTitle = rawShowData.title;
            backdropUrl = rawShowData.backdrop_url || "";
            overview = rawShowData.overview || "No overview available for this show.";

            calculateNextEpisode();

            seasonModel.clear();
            let seasons = rawShowData.seasons.sort((a, b) => a.season_number - b.season_number);

            for (let s = 0; s < seasons.length; s++) {
                seasonModel.append({
                    "seasonText": "Season " + seasons[s].season_number,
                    "seasonIndex": s
                });
            }

            if (seasons.length > 0) {
                // Make sure the saved index isn't out of bounds
                if (savedSeasonIndex >= seasons.length) {
                    savedSeasonIndex = 0;
                }

                // Restore the combo box to the remembered season
                seasonComboBox.currentIndex = savedSeasonIndex;
                loadEpisodesForSeason(savedSeasonIndex);
            }
        }).catch(function (error) {
            console.error("Failed to load show details:", error);
        });
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
                "isCompleted": ep.is_completed || false,
                "isAvailable": ep.is_available !== undefined ? ep.is_available : true
            });
        }
    }

    function calculateNextEpisode() {
        if (!rawShowData || !rawShowData.seasons)
            return;

        let seasons = rawShowData.seasons.sort((a, b) => a.season_number - b.season_number);

        for (let s = 0; s < seasons.length; s++) {
            let season = seasons[s];
            let eps = season.episodes.sort((a, b) => a.episode_number - b.episode_number);

            for (let e = 0; e < eps.length; e++) {
                let ep = eps[e];

                // Parse availability
                let epAvailable = ep.is_available !== undefined ? ep.is_available : true;

                // Skip if completed, missing, or has no file attached
                if (!ep.is_completed && epAvailable && ep.file_id !== null && ep.file_id !== -1) {
                    nextEpisode = {
                        seasonNum: season.season_number,
                        seasonIndex: s,
                        episodeNum: ep.episode_number,
                        title: ep.title,
                        fileId: ep.file_id
                    };
                    return;
                }
            }
        }
        // If it finishes the loop without returning, the show is fully watched (or no episodes exist)
        nextEpisode = null;
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

            // THE CONTINUE WATCHING BUTTON

            Row {
                id: actionsRow
                spacing: 15

                Rectangle {
                    id: continueWatchingButton
                    width: nextEpisodeText.width + 64 // Auto-sizes width to fit the text
                    height: 48
                    radius: 24
                    color: playMouseArea.containsMouse ? "#90909090" : "#66808080"

                    // Hides completely if finished the show or no files are available
                    visible: root.nextEpisode !== null

                    Behavior on color {
                        ColorAnimation {
                            duration: 150
                        }
                    }

                    Row {
                        anchors.centerIn: parent
                        spacing: 12

                        Text {
                            text: "▶"
                            color: "white"
                            font.pixelSize: 18
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            id: nextEpisodeText
                            text: root.nextEpisode ? ("Play S" + root.nextEpisode.seasonNum + " E" + root.nextEpisode.episodeNum + " • " + root.nextEpisode.title) : ""
                            color: "white"
                            font.pixelSize: 16
                            font.bold: true
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        id: playMouseArea
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        hoverEnabled: true
                        onClicked: {
                            if (root.nextEpisode) {
                                // Automatically switch the dropdown to the season about to be watched
                                savedSeasonIndex = root.nextEpisode.seasonIndex;
                                seasonComboBox.currentIndex = savedSeasonIndex;

                                // Trigger the player
                                let streamUrl = "http://127.0.0.1:8000/api/stream/" + root.nextEpisode.fileId + "?direct_play=true";
                                root.episodePlay(streamUrl, root.nextEpisode.fileId);
                            }
                        }
                    }
                }

                Button {
                    id: refreshBtn
                    width: 40
                    height: 40
                    anchors.verticalCenter: continueWatchingButton.verticalCenter
                    icon.source: "refresh.svg" // Reuse settings icon or add a refresh.svg
                    icon.color: Theme.textSecondary

                    background: Rectangle {
                        color: refreshBtn.hovered ? Theme.bgCardHover : "transparent"
                        radius: 20
                    }

                    onClicked: {
                        API.post("/api/show/" + showId + "/refresh").then(function () {
                            // Signal to the screen to reload its data
                            root.loadShowDetails();
                            root.loadEpisodesForSeason(savedSeasonIndex);
                        });
                    }
                }
            }

            Item {
                width: 1
                height: 40
            } // Margin before the Season Selector Bar

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
                                savedSeasonIndex = currentIndex;
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
                        opacity: model.isAvailable ? 1.0 : 0.6

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

                            // MISSING FILE OVERLAY: Darken the thumbnail
                            Rectangle {
                                anchors.fill: parent
                                color: "black"
                                radius: 8
                                opacity: 0.65
                                visible: !model.isAvailable
                            }

                            // MISSING FILE OVERLAY: The Red Video-Off Icon
                            Button {
                                anchors.centerIn: parent
                                icon.source: "missing.svg"
                                icon.color: "red"
                                width: 36
                                height: 36
                                icon.width: 36
                                icon.height: 36
                                opacity: 0.8
                                visible: !model.isAvailable
                                enabled: false
                                background: Item {} // Removes button styling!
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
                                    visible: !model.isAvailable
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
                            // Change to the red slash cursor
                            cursorShape: model.isAvailable ? Qt.PointingHandCursor : Qt.ForbiddenCursor

                            onClicked: {
                                // Block the click if missing
                                if (!model.isAvailable) {
                                    console.log("Episode missing! Cannot open.");
                                    return;
                                }

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
