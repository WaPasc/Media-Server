import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    // Properties passed from the model
    property int directoryId
    property string path: ""
    property string mediaType: ""

    // Signal to tell the parent to delete this item
    signal removeClicked(int id)

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

        // Media Type Badge (Movies = Blue, Shows = Green)
        Rectangle {
            width: 60
            height: 24
            radius: 12
            color: root.mediaType === "movies" ? "#3B82F6" : "#10B981"

            Text {
                anchors.centerIn: parent
                text: root.mediaType.toUpperCase()
                color: "white"
                font.pixelSize: 10
                font.bold: true
            }
        }

        // Directory Path
        Text {
            Layout.fillWidth: true
            text: root.path
            color: Theme.textColor
            font.pixelSize: 14
            elide: Text.ElideMiddle
        }

        // Remove Button
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
                onClicked: root.removeClicked(root.directoryId)
            }
        }
    }
}
