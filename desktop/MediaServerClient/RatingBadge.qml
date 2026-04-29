import QtQuick
import QtQuick.Window
import MediaServerClient

// IMDb rating badge, official logo on the left, score in a colour-graded
// pill on the right. Hidden when no rating is available.
Rectangle {
    id: root

    property real rating: 0
    property int fontSize: 14

    // Pick a colour bucket based on the score. Tuned to match how IMDb
    // ratings cluster: 4-9 
    function ratingColor(score) {
        if (score >= 9.0) return "#047857"      // emerald (elite)
        if (score >= 8.0) return "#16A34A"      // strong green
        if (score >= 7.0) return "#65A30D"      // lime
        if (score >= 6.0) return "#CA8A04"      // yellow
        if (score >= 5.0) return "#EA580C"      // orange
        if (score >= 4.0) return "#DC2626"      // red
        return "#7F1D1D"                        // dark red (disaster)
    }

    visible: rating > 0
    radius: 6
    color: Theme.bgBadge
    border.width: 1
    border.color: Theme.borderDark
    implicitWidth: row.implicitWidth + 12
    implicitHeight: row.implicitHeight + 8

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 8

        Image {
            id: imdbLogo
            source: "imdb-logo.svg"
            // SVG is 64×32 (2:1). Lock displayed dims to that aspect.
            height: root.fontSize + 8
            width: height * 2
            // Rasterise the SVG at the actual physical pixel size on the
            // current screen (logical size × devicePixelRatio). This gives
            // pixel-perfect rendering at any badge size — no fixed
            // resolution to up- or down-scale from, which is what was
            // making the small episode-row badges look blurry.
            sourceSize.width: width * Screen.devicePixelRatio
            sourceSize.height: height * Screen.devicePixelRatio
            fillMode: Image.PreserveAspectFit
            smooth: true
            anchors.verticalCenter: parent.verticalCenter
        }

        Rectangle {
            color: root.ratingColor(root.rating)
            radius: 4
            implicitWidth: scoreText.implicitWidth + 10
            implicitHeight: scoreText.implicitHeight + 4
            anchors.verticalCenter: parent.verticalCenter

            Text {
                id: scoreText
                anchors.centerIn: parent
                text: root.rating.toFixed(1)
                color: "white"
                font.pixelSize: root.fontSize
                font.bold: true
            }
        }
    }
}
