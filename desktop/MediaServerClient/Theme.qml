pragma Singleton
import QtQuick

QtObject {
    // Backgrounds
    readonly property color bgBase: "#09090B"
    readonly property color bgCard: "#171717"
    readonly property color bgOverlay: "#CC000000"

    // Accents & Borders
    readonly property color accent: "#6366F1"
    readonly property color borderMain: "#262626"
    readonly property color borderHover: "#525252"

    // Text Colors
    readonly property color textTitle: "white"
    readonly property color textPrimary: "#F5F5F5"
    readonly property color textHover: "#D4D4D8"
    readonly property color textSecondary: "#737373"
    readonly property color textMuted: "#525252"

    // Additional Backgrounds
    readonly property color bgBaseFade: "#AA09090B"
    readonly property color bgPanel: "#1A09090B"
    readonly property color bgCardHover: "#1A1A1A"
    readonly property color bgBlack: "#000000"
    readonly property color bgBadge: "#27272A"

    // Additional Borders
    readonly property color borderLight: "#1AFFFFFF"
    readonly property color borderInput: "#3F3F46"
    readonly property color borderDark: "#27272A"

    // Additional Text & Accents
    readonly property color textTertiary: "#9CA3AF"
    readonly property color accentLight: "#818CF8"
}
