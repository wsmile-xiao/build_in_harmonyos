cmake_minimum_required(VERSION 3.16)
project(test_package LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# KExiv2Qt6Config.cmake does find_dependency(Qt6Core/Qt6Gui) and the exported
# KExiv2Qt6 target links Qt6::Gui/Qt6::Core, so Qt6 has to be located first
# (libkcddb 26.04.3 test_package precedent).
find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KExiv2Qt6 CONFIG REQUIRED)

add_executable(test_package test_package.cpp)
target_link_libraries(test_package PRIVATE KExiv2Qt6 Qt6::Gui Qt6::Core)
