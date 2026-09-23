cmake_minimum_required(VERSION 3.15)
project(test_png LANGUAGES CXX)

find_package(png REQUIRED CONFIG)

add_executable(test_png test_png.cpp)
target_link_libraries(test_png PRIVATE png::png)
target_compile_features(test_png PRIVATE cxx_std_11)
