import QtQuick
import QtQuick.Controls
import QtQuick.Effects

Item {
    id: root

    // Properties passed from the model
    property int mediaId
    property string title: ""
    property string year: ""
    property string posterUrl: ""
    property bool isAvailable: true
    property bool isCompleted: false

    // Optional display properties
    property bool showCheckmark: false

    // Signals emitted to the parent
    signal clicked(int id)

    width: 220
    height: 380
    z: mouseArea.containsMouse ? 10 : 0

    Column {
        anchors.centerIn: parent
        width: 200
        spacing: 12

        scale: mouseArea.containsMouse ? 1.05 : 1.0
        Behavior on scale {
            NumberAnimation { duration: 300; easing.type: Easing.OutQuart }
        }

        // POSTER CONTAINER
        Item {
            width: 200
            height: 300

            Rectangle {
                anchors.fill: parent
                radius: 12
                color: Theme.bgCard
            }

            Image {
                id: posterImage
                anchors.fill: parent
                anchors.margins: 1
                source: root.posterUrl
                fillMode: Image.PreserveAspectCrop
                visible: false
            }

            Item {
                id: imageMask
                anchors.fill: posterImage
                layer.enabled: true
                visible: false
                Rectangle {
                    anchors.fill: parent
                    radius: 11
                    color: "black"
                }
            }

            MultiEffect {
                anchors.fill: posterImage
                source: posterImage
                maskEnabled: true
                maskSource: imageMask
                visible: root.posterUrl !== ""
            }

            Text {
                anchors.centerIn: parent
                text: "No Poster"
                color: Theme.textMuted
                font.pixelSize: 14
                visible: root.posterUrl === ""
            }

            Rectangle {
                anchors.fill: parent
                color: "black"
                radius: 12
                opacity: 0.65
                visible: !root.isAvailable
            }

            Button {
                anchors.centerIn: parent
                icon.source: "missing.svg"
                icon.color: "red"
                width: 48
                height: 48
                icon.width: 48
                icon.height: 48
                opacity: 0.8
                visible: !root.isAvailable
                enabled: false
                background: Item {}
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                radius: 12
                border.width: 1
                border.color: mouseArea.containsMouse ? Theme.borderHover : Theme.borderMain
            }

            Image {
                source: "check-circle.svg"
                width: 28
                height: 28
                sourceSize.width: 28
                sourceSize.height: 28
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 10

                visible: root.isCompleted && root.showCheckmark

                Behavior on opacity { NumberAnimation { duration: 200 } }
                opacity: visible ? 1.0 : 0.0
            }
        }

        // TEXT CONTAINER
        Column {
            width: parent.width
            spacing: 2

            Text {
                text: root.title
                color: Theme.textPrimary
                font.pixelSize: 16
                font.bold: true
                width: parent.width
                elide: Text.ElideRight
            }

            Text {
                text: root.year
                color: Theme.textSecondary
                font.pixelSize: 12
                font.bold: true
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.isAvailable ? Qt.PointingHandCursor : Qt.ForbiddenCursor

        onClicked: {
            if (!root.isAvailable) {
                console.log("Media missing! Cannot open.");
                return;
            }
            root.clicked(root.mediaId);
        }
    }
}