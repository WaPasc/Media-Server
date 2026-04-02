import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "NetworkManager.js" as API

Rectangle {
    id: root
    color: Theme.bgBase

    signal backClicked

    property string apiUrl: "http://127.0.0.1:8000/api/scanner"

    ListModel {
        id: directoryModel
    }

    Component.onCompleted: fetchDirectories()

    // --- HEADER ---
    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 80
        color: Theme.bgBase
        z: 10 // Keep header above scrolling content

        // Subtle border to separate header from scroll content
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Theme.borderMain
        }

        Button {
            id: backBtn
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.margins: 30

            contentItem: Text {
                text: "← Back"
                color: backBtn.hovered ? Theme.textHover : Theme.textSecondary
                font.pixelSize: 16
                font.bold: true
            }
            background: Item {}

            onClicked: root.backClicked()
            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.backClicked()
            }
        }

        Text {
            text: "Settings"
            color: Theme.textTitle
            font.pixelSize: 28
            font.bold: true
            anchors.centerIn: parent
        }
    }

    // --- MAIN CONTENT ---
    // ScrollView now spans the ENTIRE width and height below the header
    ScrollView {
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        clip: true
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        // Tells the scroll view to fill the available width, enabling scrolling from anywhere
        contentWidth: availableWidth

        ColumnLayout {
            // Centers the content, but gives it a wider, more breathable 650px maximum
            width: Math.min(650, parent.width - 60)
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 40 // Generous spacing between the cards

            // Top Margin Spacer
            Item {
                Layout.preferredHeight: 20
            }

            // ADD DIRECTORY CARD
            AddDirectoryCard {
                onDirectoryAdded: fetchDirectories()
            }

            //  SCAN ACTION CARD
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: scanLayout.implicitHeight + 60
                color: Theme.bgCard
                border.color: Theme.borderMain
                border.width: 1
                radius: 12

                ColumnLayout {
                    id: scanLayout
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 30
                    spacing: 20

                    Text {
                        text: "Library Scan"
                        color: Theme.textPrimary
                        font.pixelSize: 18
                        font.bold: true
                    }

                    Text {
                        text: "Manually force the server to scan all directories for new media."
                        color: Theme.textSecondary
                        font.pixelSize: 14
                    }

                    Button {
                        id: scanBtn
                        Layout.fillWidth: true
                        Layout.preferredHeight: 45
                        Layout.topMargin: 10

                        contentItem: Text {
                            text: "Trigger Full Library Scan"
                            color: Theme.textColor
                            font.pixelSize: 14
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }

                        background: Rectangle {
                            color: scanBtn.hovered ? Theme.bgCardHover : Theme.bgBase
                            border.color: scanBtn.hovered ? Theme.borderHover : Theme.borderMain
                            border.width: 1
                            radius: 8
                            Behavior on color {
                                ColorAnimation {
                                    duration: 150
                                }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: triggerScan()
                        }
                    }
                }
            }

            // MONITORED DIRECTORIES
            Rectangle {
                Layout.fillWidth: true
                // Let the card grow naturally with its content instead of using a fixed height
                Layout.preferredHeight: dirsColumn.implicitHeight + 60
                color: Theme.bgCard
                border.color: Theme.borderMain
                border.width: 1
                radius: 12
                visible: directoryModel.count > 0

                ColumnLayout {
                    id: dirsColumn
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 30
                    spacing: 20

                    Text {
                        text: "Monitored Directories"
                        color: Theme.textPrimary
                        font.pixelSize: 18
                        font.bold: true
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Repeater {
                            model: directoryModel

                            delegate: DirectoryRow {
                                directoryId: model.id
                                path: model.path
                                mediaType: model.media_type

                                onRemoveClicked: id => deleteDirectory(id)
                            }
                        }
                    }
                }
            }

            // Bottom Margin Spacer to ensure you can scroll past the last item
            Item {
                Layout.preferredHeight: 60
            }
        }
    }

    // API LOGIC
    function fetchDirectories() {
        API.get("/api/scanner/directories").then(function (dirs) {
            directoryModel.clear();
            for (var i = 0; i < dirs.length; i++) {
                let dirItem = dirs[i];

                if (dirItem.last_scanned === null) {
                    dirItem.last_scanned = "Never";
                }
                if (dirItem.error_message === null) {
                    dirItem.error_message = "";
                }

                directoryModel.append(dirItem);
            }
        }).catch(function (error) {
            console.error("Failed to load directories:", error);
        });
    }

    function deleteDirectory(id) {
        API.del("/api/scanner/directories/" + id).then(function () {
            // Success! Re-fetch the list to update the UI
            fetchDirectories();
        }).catch(function (error) {
            console.error("Failed to remove directory:", error);
            statusLabel.text = "Failed to remove directory.";
            statusLabel.color = "#EF4444";
        });
    }

    function addDirectory(path, type) {
        if (path.trim() === "") {
            statusLabel.text = "Path cannot be empty!";
            statusLabel.color = "#EF4444";
            return;
        }

        // Show loading state
        statusLabel.text = "Adding directory...";
        statusLabel.color = Theme.textMuted;

        var payload = {
            "path": path,
            "media_type": type
        };

        API.post("/api/scanner/directories", payload).then(function (data) {
            statusLabel.text = "Directory added successfully!";
            statusLabel.color = "#10B981";
            pathInput.text = ""; // Clear the text field
            fetchDirectories();  // Refresh the UI list
        }).catch(function (error) {
            console.error("Failed to add directory:", error);
            statusLabel.text = "Failed to add directory.";
            statusLabel.color = "#EF4444";
        });
    }

    function triggerScan() {
        // Show loading state
        statusLabel.text = "Initializing scan...";
        statusLabel.color = Theme.textMuted;

        API.post("/api/scanner/scan").then(function (data) {
            statusLabel.text = "Scan started! Check backend logs.";
            statusLabel.color = "#10B981";
        }).catch(function (error) {
            console.error("Failed to start scan:", error);
            statusLabel.text = "Failed to start scan.";
            statusLabel.color = "#EF4444";
        });
    }
}
