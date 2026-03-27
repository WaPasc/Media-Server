import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    color: Theme.bgBase

    signal backClicked

    // Replace with actual backend URL
    property string apiUrl: "http://127.0.0.1:8000/api/scanner"

    // HEADER
    Item {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 80

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
            background: Item {} // Transparent background

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

    // MAIN CONTENT
    ColumnLayout {
        anchors.top: header.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 20
        width: 500
        spacing: 30

        // ADD DIRECTORY CARD
        Rectangle {
            Layout.fillWidth: true
            height: 320
            color: Theme.bgCard
            border.color: Theme.borderMain
            border.width: 1
            radius: 12

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 25
                spacing: 15

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
                    Layout.bottomMargin: 10
                }

                // PATH INPUT
                TextField {
                    id: pathInput
                    Layout.fillWidth: true
                    Layout.preferredHeight: 45
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

                // MEDIA TYPE COMBOBOX
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
                        elide: Text.ElideRight
                    }

                    background: Rectangle {
                        color: Theme.bgBase
                        border.color: mediaTypeCombo.activeFocus || mediaTypeCombo.popup.visible ? Theme.accent : Theme.borderInput
                        border.width: 1
                        radius: 8

                        // Smoothly transition the border glow
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
                            // Keep it highlighted while the menu is open
                            context.fillStyle = mediaTypeCombo.pressed || mediaTypeCombo.popup.visible ? Theme.textPrimary : Theme.textSecondary;
                            context.fill();
                        }
                    }

                    popup: Popup {
                        y: mediaTypeCombo.height + 4
                        width: mediaTypeCombo.width
                        // calculate height to prevent layout snapping
                        implicitHeight: Math.min(contentItem.contentHeight + topPadding + bottomPadding, 200)
                        padding: 4

                        // Smooth fade-in and fade-out animations
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
                            // Keep the model permanently attached so it doesn't rebuild and jump on click
                            model: mediaTypeCombo.delegateModel
                            currentIndex: mediaTypeCombo.highlightedIndex
                            ScrollIndicator.vertical: ScrollIndicator {}
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
                            // Check BOTH hovered (mouse) and highlighted (keyboard)
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
                            // Smoothly shift between the two solid card colors
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

                // SUBMIT BUTTON
                Button {
                    id: addBtn
                    Layout.fillWidth: true
                    Layout.preferredHeight: 45
                    Layout.topMargin: 10

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

                // STATUS LABEL
                Label {
                    id: statusLabel
                    text: ""
                    color: Theme.textMuted
                    font.pixelSize: 14
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // SCAN ACTION CARD
        Rectangle {
            Layout.fillWidth: true
            height: 140
            color: Theme.bgCard
            border.color: Theme.borderMain
            border.width: 1
            radius: 12

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 25
                spacing: 15

                Text {
                    text: "Library Scan"
                    color: Theme.textPrimary
                    font.pixelSize: 18
                    font.bold: true
                }

                Button {
                    id: scanBtn
                    Layout.fillWidth: true
                    Layout.preferredHeight: 45

                    contentItem: Text {
                        text: "Trigger Full Library Scan"
                        color: Theme.textColor
                        font.pixelSize: 14
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }

                    background: Rectangle {
                        // Lighter border when hovered, dark card background otherwise
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
    }

    // API LOGIC
    function addDirectory(path, type) {
        if (path.trim() === "") {
            statusLabel.text = "Path cannot be empty!";
            statusLabel.color = "#EF4444"; // Explicit red for error
            return;
        }

        var xhr = new XMLHttpRequest();
        xhr.open("POST", apiUrl + "/directories");
        xhr.setRequestHeader("Content-Type", "application/json");

        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    statusLabel.text = "Directory added successfully!";
                    statusLabel.color = "#10B981"; // Emerald green for success
                    pathInput.text = "";
                } else {
                    statusLabel.text = "Error: " + xhr.responseText;
                    statusLabel.color = "#EF4444"; // Red for error
                }
            }
        };

        statusLabel.text = "Adding directory...";
        statusLabel.color = Theme.textMuted;
        xhr.send(JSON.stringify({
            "path": path,
            "media_type": type
        }));
    }

    function triggerScan() {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", apiUrl + "/scan");
        xhr.setRequestHeader("Content-Type", "application/json");

        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    statusLabel.text = "Scan started! Check backend logs.";
                    statusLabel.color = "#10B981"; // Emerald green
                } else {
                    statusLabel.text = "Failed to start scan.";
                    statusLabel.color = "#EF4444";
                }
            }
        };

        statusLabel.text = "Initializing scan...";
        statusLabel.color = Theme.textMuted;
        xhr.send();
    }
}
