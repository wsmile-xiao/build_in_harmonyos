cmake_minimum_required(VERSION 3.16)
project(qtmultimedia_test LANGUAGES CXX)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Gui Multimedia)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_17)
target_link_libraries(
    test_package PRIVATE Qt6::Multimedia Qt6::Gui Qt6::Core
)
