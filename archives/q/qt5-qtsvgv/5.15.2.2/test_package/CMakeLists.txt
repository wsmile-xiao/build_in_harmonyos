cmake_minimum_required(VERSION 3.16)
project(test_qt5svgv CXX)

# CMakeDeps exposes the package-level qtsvg config and the aggregate Qt5
# provider config (the provider's components are targets under Qt5Config.cmake).
find_package(qt5-qtsvgv CONFIG REQUIRED)
find_package(Qt5 CONFIG REQUIRED COMPONENTS Core Gui)

add_executable(test_qt5svgv test.cpp)
target_link_libraries(test_qt5svgv PRIVATE qt5-qtsvgv::qt5-qtsvgv qt5-qtbase::qt5-qtbase)
