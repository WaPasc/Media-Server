import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import MediaServerClient
import "NetworkManager.js" as API

Item {
    id: root

    // Signals to talk to Main.qml
    signal backClicked
    signal moviePlay(string streamUrl, int fileId)

    property int movieId: -1
    property string movieTitle: ""
    property string movieYear: ""
    property string backdropUrl: ""
    property string overview: ""
    property int fileId: -1

    onMovieIdChanged: {
        if (movieId !== -1)
            loadMovieDetails();
    }

    onVisibleChanged: {
        if (visible && movieId !== -1) {
            loadMovieDetails();
        }
    }

    function loadMovieDetails() {
        API.get("/api/movie/" + movieId).then(function (data) {
            movieTitle = data.title || "";
            movieYear = data.year ? data.year.toString() : "Unknown Year";
            backdropUrl = data.backdrop_url || "";
            overview = data.overview || "No overview available for this title.";
            fileId = data.file_id || -1;
        }).catch(function (error) {
            console.error("Failed to load movie details:", error);
        });
    }

    // STATIC BACKGROUND
    Rectangle {
        anchors.fill: parent
        color: Theme.bgBase

        Item {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: parent.height * 0.75 // h-[75vh]

            Image {
                anchors.fill: parent
                source: backdropUrl
                fillMode: Image.PreserveAspectCrop
                verticalAlignment: Image.AlignTop
                opacity: 0.60
            }

            // Vertical Fade
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
        }
    }

    // MAIN SCROLLING CONTENT
    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        Column {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(parent.width - 96, 1280)

            // Top spacing
            Item {
                width: 1
                height: root.height * 0.40
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
            }

            // Title
            Text {
                text: movieTitle
                color: Theme.textTitle
                font.pixelSize: 72
                font.bold: true
                font.letterSpacing: -1
                width: parent.width
                wrapMode: Text.WordWrap
            }

            Item {
                width: 1
                height: 16
            }

            // Year
            Text {
                text: movieYear
                color: Theme.textHover
                font.pixelSize: 24
                font.bold: true
            }

            Item {
                width: 1
                height: 40
            }

            // Play Button
            Button {
                id: playBtn
                width: 220
                height: 56

                contentItem: Row {
                    anchors.centerIn: parent
                    spacing: 12
                    Item {
                        height: 1
                        width: 12
                    }
                    Text {
                        text: "▶" // Unicode substitute for the SVG Play icon
                        font.pixelSize: 20
                        color: "black"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: "Play Movie"
                        font.pixelSize: 20
                        font.bold: true
                        color: "black"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                background: Rectangle {
                    color: "white"
                    radius: 8
                    scale: playBtn.hovered ? 1.05 : 1.0
                    Behavior on scale {
                        NumberAnimation {
                            duration: 150
                        }
                    }
                }

                onClicked: {
                    if (fileId !== -1) {
                        let streamUrl = "http://127.0.0.1:8000/api/stream/" + fileId + "?direct_play=true";
                        root.moviePlay(streamUrl, fileId);
                    } else {
                        console.log("No physical file is attached to this movie!");
                    }
                }

                // Ensures the mouse turns into a pointer finger without blocking the button click
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.NoButton
                }
            }

            Item {
                width: 1
                height: 48
            } // mb-12

            // Overview Container
            Rectangle {
                width: Math.min(parent.width, 768) // max-w-3xl
                color: Theme.bgGlass
                radius: 16
                border.color: Theme.borderLight

                implicitHeight: overviewCol.implicitHeight + 48 // Dynamically size based on text length

                Column {
                    id: overviewCol
                    anchors.fill: parent
                    anchors.margins: 24
                    spacing: 12

                    Text {
                        text: "Overview"
                        color: Theme.textPrimary
                        font.pixelSize: 20
                        font.bold: true
                    }

                    Text {
                        text: overview
                        color: Theme.textHover
                        font.pixelSize: 18
                        width: parent.width
                        wrapMode: Text.WordWrap
                        lineHeight: 1.4
                    }
                }
            }

            Item {
                width: 1
                height: 80
            } // pb-20
        }
    }
}
