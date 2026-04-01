cmake_minimum_required(VERSION 3.16)

project(MediaServerClient VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Quick)

# Find mpv
find_package(PkgConfig REQUIRED)
pkg_check_modules(MPV REQUIRED mpv)

qt_standard_project_setup(REQUIRES 6.10)

qt_add_executable(appMediaServerClient
    main.cpp
)

set_source_files_properties(Theme.qml PROPERTIES
    QT_QML_SINGLETON_TYPE TRUE
)

qt_add_qml_module(appMediaServerClient
    URI MediaServerClient
    QML_FILES
        Main.qml
        LibraryScreen.qml
        PlayerScreen.qml
        ShowDetailScreen.qml
        MovieDetailScreen.qml
        SettingsScreen.qml
        Theme.qml
        HistoryScreen.qml
        MediaCard.qml
        LandscapeCard.qml

    SOURCES
        MpvItem.h
        MpvItem.cpp

    RESOURCES
        check-circle.svg
        settings.svg
        volume-up.svg
        volume-mute.svg
        subtitles.svg
        fullscreen-max.svg
        fullscreen-min.svg
        play.svg
        pause.svg
        back.svg
        missing.svg
        history.svg
)

# Qt for iOS sets MACOSX_BUNDLE_GUI_IDENTIFIER automatically since Qt 6.1.
# If you are developing for iOS or macOS you should consider setting an
# explicit, fixed bundle identifier manually though.
set_target_properties(appMediaServerClient PROPERTIES
#    MACOSX_BUNDLE_GUI_IDENTIFIER com.example.appMediaServerClient
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)

target_link_libraries(appMediaServerClient
    PRIVATE Qt6::Quick
    PRIVATE ${MPV_LIBRARIES}
)
target_include_directories(appMediaServerClient PRIVATE ${MPV_INCLUDE_DIRS})

install(TARGETS appMediaServerClient
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
