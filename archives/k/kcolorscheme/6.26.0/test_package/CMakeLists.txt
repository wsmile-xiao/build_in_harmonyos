cmake_minimum_required(VERSION 3.15)
project(test_kcolorscheme CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6ColorScheme REQUIRED)

add_executable(test_kcolorscheme test.cpp)
target_link_libraries(test_kcolorscheme PRIVATE KF6::ColorScheme)
