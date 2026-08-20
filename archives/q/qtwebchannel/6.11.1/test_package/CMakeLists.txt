cmake_minimum_required(VERSION 3.16)
project(qtwebchannel_test LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core WebChannel)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_17)
set_target_properties(test_package PROPERTIES AUTOMOC ON)
target_link_libraries(
    test_package PRIVATE Qt6::WebChannel Qt6::Core
)
