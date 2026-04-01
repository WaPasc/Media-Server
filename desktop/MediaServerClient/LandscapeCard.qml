import QtQuick
import QtQuick.Controls
import QtQuick.Effects

Item {
    id: root

    // Properties
    property int fileId
    property string imageUrl: ""
    property string mainTitle: ""
    property string subTitle: ""

    // Progress Bar configuration
    property real progress: 0.0
    property bool showProgressBar: false

    // Signals
    signal clicked(int fileId)

    // The scale behavior triggers off this mouse area
    z: mouseArea.containsMouse ? 10 : 0

    Column {
        anchors.centerIn: parent
        width: parent.width * 0.95 // Slightly smaller than parent to allow scaling room
        spacing: 12

        scale: mouseArea.containsMouse ? 1.05 : 1.0
        Behavior on scale {
            NumberAnimation {
                duration: 200
                easing.type: Easing.OutQuart
            }
        }

        // THUMBNAIL CONTAINER
        Item {
            width: parent.width
            height: width * (9 / 16) // Force perfect 16:9 aspect ratio

            Rectangle {
                anchors.fill: parent
                radius: 12
                color: Theme.bgCard
            }

            Item {
                id: contentToMask
                anchors.fill: parent
                anchors.margins: 1
                visible: false
                layer.enabled: true

                Image {
                    anchors.fill: parent
                    source: root.imageUrl
                    fillMode: Image.PreserveAspectCrop
                }

                // Conditional Progress Bar Setup
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 40
                    visible: root.showProgressBar
                    gradient: Gradient {
                        GradientStop {
                            position: 0.0
                            color: "transparent"
                        }
                        GradientStop {
                            position: 1.0
                            color: "#CC000000"
                        }
                    }
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 4
                    color: "transparent"
                    visible: root.showProgressBar
                }
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    width: parent.width * (root.progress / 100)
                    height: 4
                    color: Theme.accent
                    visible: root.showProgressBar
                }
            }

            Item {
                id: imageMask
                anchors.fill: contentToMask
                layer.enabled: true
                visible: false

                Rectangle {
                    anchors.fill: parent
                    radius: 11
                    color: "black"
                }
            }

            MultiEffect {
                anchors.fill: contentToMask
                source: contentToMask
                maskEnabled: true
                maskSource: imageMask
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                radius: 12
                border.width: 1
                border.color: mouseArea.containsMouse ? Theme.borderHover : Theme.borderMain
                Behavior on border.color {
                    ColorAnimation {
                        duration: 150
                    }
                }
            }
        }

        // TEXT INFO
        Column {
            width: parent.width
            spacing: 4

            Text {
                text: root.mainTitle
                color: mouseArea.containsMouse ? Theme.accentLight : Theme.textPrimary
                font.pixelSize: 16
                font.bold: true
                width: parent.width
                elide: Text.ElideRight
                Behavior on color {
                    ColorAnimation {
                        duration: 150
                    }
                }
            }

            Text {
                text: root.subTitle
                color: Theme.textSecondary
                font.pixelSize: 13
                width: parent.width
                elide: Text.ElideRight
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor

        onClicked: {
            root.clicked(root.fileId);
        }
    }
}
