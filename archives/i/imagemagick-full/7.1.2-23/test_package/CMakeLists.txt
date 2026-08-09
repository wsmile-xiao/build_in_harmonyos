cmake_minimum_required(VERSION 3.15)
project(test_imagemagick_full C)

find_package(imagemagick-full REQUIRED)

add_executable(test_imagemagick_full test.c)
target_link_libraries(test_imagemagick_full imagemagick-full::imagemagick-full)
