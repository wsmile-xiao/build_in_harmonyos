cmake_minimum_required(VERSION 3.16)
project(test_qtpositioning LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core Positioning)

add_executable(test_qtpositioning test_qtpositioning.cpp)
target_compile_features(test_qtpositioning PRIVATE cxx_std_17)
target_link_libraries(
    test_qtpositioning
    PRIVATE Qt6::Core Qt6::Positioning
)
