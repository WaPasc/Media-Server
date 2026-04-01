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
            Rectangle {
                Layout.fillWidth: true
                // Dynamic height based on content + margins
                Layout.preferredHeight: addDirLayout.implicitHeight + 60
                color: Theme.bgCard
                border.color: Theme.borderMain
                border.width: 1
                radius: 12

                ColumnLayout {
                    id: addDirLayout
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 30 // Wider inner margins
                    spacing: 20

                    Text {
                        text: "Add Media Directory"
                        color: Theme.textPrimary
                        font.pixelSize: 18
                        font.bold: true
                    }

                    Text {
                        text: "Tell the media server where to look for your files."
                        color: Theme.textSecondary
                        font.pixelSize: 14
                    }

                    TextField {
                        id: pathInput
                        Layout.fillWidth: true
                        Layout.preferredHeight: 45
                        Layout.topMargin: 10
                        placeholderText: "/path/to/media"
                        color: Theme.textColor
                        font.pixelSize: 14
                        leftPadding: 15

                        background: Rectangle {
                            color: Theme.bgBase
                            border.color: pathInput.activeFocus ? Theme.accent : Theme.borderInput
                            border.width: 1
                            radius: 8
                        }
                    }

                    ComboBox {
                        id: mediaTypeCombo
                        Layout.fillWidth: true
                        Layout.preferredHeight: 45
                        model: ["movies", "shows"]

                        contentItem: Text {
                            text: mediaTypeCombo.displayText
                            color: Theme.textColor
                            font.pixelSize: 14
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 15
                        }

                        background: Rectangle {
                            color: Theme.bgBase
                            border.color: mediaTypeCombo.activeFocus || mediaTypeCombo.popup.visible ? Theme.accent : Theme.borderInput
                            border.width: 1
                            radius: 8
                            Behavior on border.color {
                                ColorAnimation {
                                    duration: 150
                                }
                            }
                        }

                        indicator: Canvas {
                            id: canvas
                            x: mediaTypeCombo.width - width - 15
                            y: mediaTypeCombo.topPadding + (mediaTypeCombo.availableHeight - height) / 2
                            width: 10
                            height: 6
                            contextType: "2d"

                            Connections {
                                target: mediaTypeCombo
                                function onPressedChanged() {
                                    canvas.requestPaint();
                                }
                            }

                            onPaint: {
                                var context = canvas.getContext("2d");
                                context.reset();
                                context.moveTo(0, 0);
                                context.lineTo(width, 0);
                                context.lineTo(width / 2, height);
                                context.closePath();
                                context.fillStyle = mediaTypeCombo.pressed || mediaTypeCombo.popup.visible ? Theme.textPrimary : Theme.textSecondary;
                                context.fill();
                            }
                        }

                        popup: Popup {
                            y: mediaTypeCombo.height + 4
                            width: mediaTypeCombo.width
                            implicitHeight: Math.min(contentItem.contentHeight + topPadding + bottomPadding, 200)
                            padding: 4

                            enter: Transition {
                                NumberAnimation {
                                    property: "opacity"
                                    from: 0.0
                                    to: 1.0
                                    duration: 150
                                    easing.type: Easing.OutQuad
                                }
                            }
                            exit: Transition {
                                NumberAnimation {
                                    property: "opacity"
                                    from: 1.0
                                    to: 0.0
                                    duration: 100
                                    easing.type: Easing.InQuad
                                }
                            }

                            contentItem: ListView {
                                clip: true
                                model: mediaTypeCombo.delegateModel
                                currentIndex: mediaTypeCombo.highlightedIndex
                            }

                            background: Rectangle {
                                color: Theme.bgCard
                                border.color: Theme.borderMain
                                border.width: 1
                                radius: 8
                            }
                        }

                        delegate: ItemDelegate {
                            id: itemDelegate
                            width: ListView.view.width
                            height: 40
                            hoverEnabled: true

                            contentItem: Text {
                                text: modelData
                                color: itemDelegate.hovered || itemDelegate.highlighted ? Theme.textTitle : Theme.textColor
                                font.pixelSize: 14
                                verticalAlignment: Text.AlignVCenter
                                leftPadding: 11
                                Behavior on color {
                                    ColorAnimation {
                                        duration: 100
                                    }
                                }
                            }

                            background: Rectangle {
                                color: itemDelegate.hovered || itemDelegate.highlighted ? Theme.bgCardHover : Theme.bgCard
                                radius: 4
                                Behavior on color {
                                    ColorAnimation {
                                        duration: 100
                                    }
                                }
                            }
                        }
                    }

                    Button {
                        id: addBtn
                        Layout.fillWidth: true
                        Layout.preferredHeight: 45
                        Layout.topMargin: 15

                        contentItem: Text {
                            text: "Add Directory"
                            color: "white"
                            font.pixelSize: 14
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }

                        background: Rectangle {
                            color: addBtn.hovered ? Theme.accentLight : Theme.accent
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
                            onClicked: addDirectory(pathInput.text, mediaTypeCombo.currentText)
                        }
                    }

                    Label {
                        id: statusLabel
                        text: ""
                        color: Theme.textMuted
                        font.pixelSize: 14
                        Layout.alignment: Qt.AlignHCenter
                    }
                }
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

                    // This merges the items into the main page so there is only ONE smooth scrollbar
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Repeater {
                            model: directoryModel

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 50
                                color: Theme.bgBase
                                border.color: Theme.borderMain
                                border.width: 1
                                radius: 8

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 15

                                    Rectangle {
                                        width: 60
                                        height: 24
                                        radius: 12
                                        color: model.media_type === "movies" ? "#3B82F6" : "#10B981"

                                        Text {
                                            anchors.centerIn: parent
                                            text: model.media_type.toUpperCase()
                                            color: "white"
                                            font.pixelSize: 10
                                            font.bold: true
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: model.path
                                        color: Theme.textColor
                                        font.pixelSize: 14
                                        elide: Text.ElideMiddle
                                    }

                                    Button {
                                        id: delBtn
                                        Layout.preferredWidth: 80
                                        Layout.preferredHeight: 32

                                        contentItem: Text {
                                            text: "Remove"
                                            color: delBtn.hovered ? "#FFFFFF" : "#EF4444"
                                            font.pixelSize: 12
                                            font.bold: true
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                        }

                                        background: Rectangle {
                                            color: delBtn.hovered ? "#EF4444" : "transparent"
                                            border.color: "#EF4444"
                                            border.width: 1
                                            radius: 6
                                            Behavior on color {
                                                ColorAnimation {
                                                    duration: 150
                                                }
                                            }
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: deleteDirectory(model.id)
                                        }
                                    }
                                }
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
