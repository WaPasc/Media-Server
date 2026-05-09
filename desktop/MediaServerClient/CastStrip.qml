import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import MediaServerClient

// Cast list block. Mirrors the styling of the Overview container on the
// detail screens: glass background, light border, 16 radius. Compact mode
// scrolls horizontally; expanded mode wraps into a grid for a "See all"
// experience without leaving the detail screen.
Rectangle {
    id: root

    property var castModel: []
    property int totalCastCount: 0
    property bool expanded: false

    // Asks the parent screen to fetch the full cast list (cast_limit=5000).
    // The parent re-loads, replaces castModel + totalCastCount, then flips
    // `expanded` to true.
    signal seeAllRequested

    color: Theme.bgGlass
    radius: 16
    border.color: Theme.borderLight

    implicitHeight: contentColumn.implicitHeight + 48
    visible: castModel && castModel.length > 0

    Component {
        id: castDelegate

        Item {
            id: castCell
            width: 110
            height: 180

            scale: castMouse.containsMouse ? 1.05 : 1.0
            Behavior on scale {
                NumberAnimation {
                    duration: 120
                }
            }

            Column {
                anchors.fill: parent
                spacing: 8

                // Circular avatar
                Item {
                    id: avatarContainer
                    width: 96
                    height: 96
                    anchors.horizontalCenter: parent.horizontalCenter

                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: Theme.bgBadge
                    }

                    Image {
                        id: avatar
                        anchors.fill: parent
                        source: modelData.profile_url || ""
                        fillMode: Image.PreserveAspectCrop
                        visible: false

                        onStatusChanged: {
                            if (status === Image.Error
                                && source.toString() !== modelData.profile_url_fallback
                                && modelData.profile_url_fallback) {
                                source = modelData.profile_url_fallback;
                            }
                        }
                    }

                    Item {
                        id: avatarMask
                        anchors.fill: avatar
                        layer.enabled: true
                        visible: false
                        Rectangle {
                            anchors.fill: parent
                            radius: width / 2
                            color: "black"
                        }
                    }

                    MultiEffect {
                        anchors.fill: avatar
                        source: avatar
                        maskEnabled: true
                        maskSource: avatarMask
                        visible: !!modelData.profile_url
                    }

                    // Initials fallback when no profile image
                    Text {
                        anchors.centerIn: parent
                        visible: !modelData.profile_url
                        text: (modelData.name || "?").substring(0, 1).toUpperCase()
                        color: Theme.textTertiary
                        font.pixelSize: 32
                        font.bold: true
                    }
                }

                Text {
                    text: modelData.name || ""
                    color: Theme.textPrimary
                    font.pixelSize: 13
                    font.bold: true
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                Text {
                    text: modelData.character || ""
                    color: Theme.textTertiary
                    font.pixelSize: 11
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }
            }

            MouseArea {
                id: castMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (modelData.tmdb_person_id) {
                        Qt.openUrlExternally(
                            "https://www.themoviedb.org/person/" + modelData.tmdb_person_id
                        );
                    }
                }
            }
        }
    }

    Column {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        // Header: title + See all / Show less
        Item {
            width: parent.width
            height: 28

            Text {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: "Cast"
                color: Theme.textPrimary
                font.pixelSize: 20
                font.bold: true
            }

            Button {
                id: seeAllBtn
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                visible: root.totalCastCount > root.castModel.length || root.expanded
                text: root.expanded
                      ? "Show less"
                      : ("See all (" + root.totalCastCount + ")")
                font.pixelSize: 13
                font.bold: true
                palette.buttonText: Theme.textHover

                background: Rectangle {
                    color: seeAllBtn.hovered ? Theme.bgCardHover : "transparent"
                    radius: 8
                    border.color: seeAllBtn.hovered ? Theme.borderHover : Theme.borderDark
                }

                contentItem: Text {
                    text: seeAllBtn.text
                    color: seeAllBtn.hovered ? Theme.textTitle : Theme.textHover
                    font: seeAllBtn.font
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    leftPadding: 12
                    rightPadding: 12
                }

                onClicked: {
                    if (root.expanded) {
                        root.expanded = false;
                    } else if (root.totalCastCount > root.castModel.length) {
                        root.seeAllRequested();
                    } else {
                        root.expanded = true;
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    acceptedButtons: Qt.NoButton
                }
            }
        }

        // Compact horizontal strip
        ListView {
            visible: !root.expanded
            width: parent.width
            height: 200
            orientation: ListView.Horizontal
            spacing: 16
            clip: true
            interactive: true
            model: root.expanded ? null : root.castModel
            delegate: castDelegate
        }

        // Expanded wrap grid
        Flow {
            visible: root.expanded
            width: parent.width
            spacing: 16

            Repeater {
                model: root.expanded ? root.castModel : null
                delegate: castDelegate
            }
        }
    }
}
