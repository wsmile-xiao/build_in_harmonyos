cmake_minimum_required(VERSION 3.16)
project(qtlanguageserver_test LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core)
find_package(Qt6LanguageServerPrivate 6.11.1 REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_17)
target_link_libraries(
    test_package PRIVATE Qt6::LanguageServerPrivate Qt6::Core
)
