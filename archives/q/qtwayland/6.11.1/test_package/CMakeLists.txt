cmake_minimum_required(VERSION 3.16)
project(test_qtwayland LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# qtbase/6.11.1.2 provides Qt6WaylandClient library and cmake config.
# The qtwayland package provides Qt6WaylandClientFeaturesPrivate module
# (feature definition headers) on top of qtbase.
find_package(Qt6 REQUIRED COMPONENTS Core Gui WaylandClient)
find_package(Qt6WaylandClientFeaturesPrivate REQUIRED)

add_executable(test_qtwayland test_qtwayland.cpp)
target_link_libraries(test_qtwayland PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::WaylandClient
    Qt6::WaylandClientFeaturesPrivate
)
