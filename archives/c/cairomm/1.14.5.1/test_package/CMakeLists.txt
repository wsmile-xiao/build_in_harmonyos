cmake_minimum_required(VERSION 3.12)
project(test_cairomm CXX)

find_package(cairomm-1.0 REQUIRED CONFIG)
find_package(freetype REQUIRED CONFIG)
find_package(fontconfig REQUIRED CONFIG)
find_package(Freetype REQUIRED)
find_package(Fontconfig REQUIRED)

add_executable(test_cairomm test.cpp)
target_link_libraries(test_cairomm cairomm-1.0::cairomm freetype::freetype fontconfig::fontconfig)
target_include_directories(test_cairomm PRIVATE ${FREETYPE_INCLUDE_DIRS} ${FONTCONFIG_INCLUDE_DIRS})
set_target_properties(test_cairomm PROPERTIES CXX_STANDARD 14)
