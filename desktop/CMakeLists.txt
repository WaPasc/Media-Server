cmake_minimum_required(VERSION 3.16)
project(MediaServerDesktop VERSION 0.1 LANGUAGES CXX)

# Use modern C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Qt6
find_package(Qt6 REQUIRED COMPONENTS Widgets)

# Find libmpv using pkg-config
find_package(PkgConfig REQUIRED)
pkg_check_modules(MPV REQUIRED mpv)

# Create the executable from our C++ files
add_executable(MediaServerDesktop
    main.cpp
    # We will add MpvWidget.cpp here in the next step
)

# Link Qt and MPV to our app
target_link_libraries(MediaServerDesktop PRIVATE 
    Qt6::Widgets 
    ${MPV_LIBRARIES}
)
target_include_directories(MediaServerDesktop PRIVATE ${MPV_INCLUDE_DIRS})