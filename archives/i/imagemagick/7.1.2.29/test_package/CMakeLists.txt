cmake_minimum_required(VERSION 3.15)
project(test_imagemagick C)

find_package(ImageMagick REQUIRED COMPONENTS MagickWand)

add_executable(test_imagemagick test_imagemagick.c)
target_link_libraries(test_imagemagick PRIVATE ImageMagick::MagickWand)

enable_testing()
add_test(NAME test_imagemagick
         COMMAND test_imagemagick
         WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
