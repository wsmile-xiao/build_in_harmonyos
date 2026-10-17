cmake_minimum_required(VERSION 3.16)
project(test_layer_shell_qt LANGUAGES CXX)

find_package(Qt6 6.9 CONFIG REQUIRED COMPONENTS Gui WaylandClient)
find_package(Qt6WaylandClientPrivate 6.11.1 REQUIRED NO_MODULE)
find_package(libxkbcommon CONFIG REQUIRED)
add_library(PkgConfig::XKBCOMMON INTERFACE IMPORTED GLOBAL)
target_link_libraries(PkgConfig::XKBCOMMON INTERFACE libxkbcommon::libxkbcommon)
find_package(LayerShellQt 6.5 CONFIG REQUIRED)

add_executable(test_layer_shell_qt test_layer_shell_qt.cpp)
target_link_libraries(test_layer_shell_qt PRIVATE LayerShellQt::Interface Qt6::Gui)
