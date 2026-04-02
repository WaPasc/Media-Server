import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "NetworkManager.js" as API

Rectangle {
    id: root

    // Tell the parent screen when a directory was successfully added
    signal directoryAdded()

    Layout.fillWidth: true
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
        anchors.margins: 30
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
                Behavior on border.color { ColorAnimation { duration: 150 } }
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
                    function onPressedChanged() { canvas.requestPaint(); }
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

                enter: Transition { NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 150; easing.type: Easing.OutQuad } }
                exit: Transition { NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 100; easing.type: Easing.InQuad } }

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
                    Behavior on color { ColorAnimation { duration: 100 } }
                }

                background: Rectangle {
                    color: itemDelegate.hovered || itemDelegate.highlighted ? Theme.bgCardHover : Theme.bgCard
                    radius: 4
                    Behavior on color { ColorAnimation { duration: 100 } }
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
                Behavior on color { ColorAnimation { duration: 150 } }
            }

            MouseArea {
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: root.addDirectory()
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

    // INTERNAL COMPONENT LOGIC
    function addDirectory() {
        let path = pathInput.text;
        let type = mediaTypeCombo.currentText;

        if (path.trim() === "") {
            statusLabel.text = "Path cannot be empty!";
            statusLabel.color = "#EF4444";
            return;
        }

        statusLabel.text = "Adding directory...";
        statusLabel.color = Theme.textMuted;

        var payload = {
            "path": path,
            "media_type": type
        };

        API.post("/api/scanner/directories", payload)
            .then(function(data) {
                statusLabel.text = "Directory added successfully!";
                statusLabel.color = "#10B981";
                pathInput.text = "";
                // Tell the parent screen to refresh!
                root.directoryAdded();
            })
            .catch(function(error) {
                console.error("Failed to add directory:", error);
                statusLabel.text = "Failed to add directory.";
                statusLabel.color = "#EF4444";
            });
    }
}