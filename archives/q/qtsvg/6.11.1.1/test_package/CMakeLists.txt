cmake_minimum_required(VERSION 3.16)
project(test_qtsvg LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Svg Widgets)

add_executable(test_qtsvg test_qtsvg.cpp)
target_compile_features(test_qtsvg PRIVATE cxx_std_17)
target_link_libraries(
    test_qtsvg
    PRIVATE Qt6::Svg Qt6::Widgets
)
