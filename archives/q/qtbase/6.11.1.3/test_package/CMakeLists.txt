cmake_minimum_required(VERSION 3.16)
project(test_qtbase LANGUAGES C CXX)

find_package(
    Qt6 6.11.1 REQUIRED
    COMPONENTS Core DBus Network Gui Widgets Xml Sql PrintSupport
               WaylandClient
)
find_package(Qt6WaylandClientPrivate 6.11.1 REQUIRED NO_MODULE)
find_package(WaylandScanner REQUIRED)
find_package(Wayland 1.15 REQUIRED COMPONENTS Client Server Cursor Egl)
find_package(XKB 0.9 REQUIRED)

foreach(required_target IN ITEMS
        Qt6::WaylandClient
        Qt6::WaylandClientPrivate
        Qt6::Sql
        Qt6::PrintSupport
        Qt6::qtwaylandscanner
        Wayland::Scanner
        Wayland::Client
        Wayland::Server
        Wayland::Cursor
        Wayland::Egl
        XKB::XKB)
    if(NOT TARGET ${required_target})
        message(FATAL_ERROR "Missing required target: ${required_target}")
    endif()
endforeach()

add_executable(test_qtbase test_qtbase.cpp)
target_compile_features(test_qtbase PRIVATE cxx_std_17)
target_link_libraries(
    test_qtbase
    PRIVATE
        Qt6::Core
        Qt6::DBus
        Qt6::Network
        Qt6::Gui
        Qt6::Widgets
        Qt6::Xml
        Qt6::Sql
        Qt6::PrintSupport
        Qt6::WaylandClient
        Qt6::WaylandClientPrivate
        Wayland::Client
        XKB::XKB
)

add_executable(test_wayland_codegen test_wayland_codegen.cpp)
target_compile_features(test_wayland_codegen PRIVATE cxx_std_17)
target_link_libraries(
    test_wayland_codegen
    PRIVATE
        Qt6::Core
        Qt6::WaylandClient
        Qt6::WaylandClientPrivate
        Wayland::Client
)
qt6_generate_wayland_protocol_client_sources(
    test_wayland_codegen
    PRIVATE_CODE
    FILES "${CMAKE_CURRENT_SOURCE_DIR}/qtbase-test.xml"
)
target_link_libraries(test_wayland_codegen PRIVATE Wayland::Egl)

# Exercise the installed CMake platform rules and automatic build-tree RPATH.
add_library(qtbase_consumer_bridge SHARED consumer_bridge.cpp)
target_compile_features(qtbase_consumer_bridge PRIVATE cxx_std_17)
target_link_libraries(qtbase_consumer_bridge PRIVATE Qt6::Core)
target_link_libraries(test_wayland_codegen PRIVATE qtbase_consumer_bridge)
