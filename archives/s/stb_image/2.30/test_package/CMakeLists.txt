cmake_minimum_required(VERSION 3.15)
project(test_stb_image C)

find_package(stb_image REQUIRED CONFIG)

add_executable(test_stb_image test_stb_image.c)
target_link_libraries(test_stb_image stb::image)
target_compile_definitions(test_stb_image PRIVATE STB_IMAGE_IMPLEMENTATION)
