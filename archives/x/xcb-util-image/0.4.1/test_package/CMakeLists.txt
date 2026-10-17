cmake_minimum_required(VERSION 3.15)
project(test_xcb_image C)

if(DEFINED CMAKE_FIND_ROOT_PATH_MODE_PACKAGE)
    set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)
endif()

find_package(xcb-util-image REQUIRED)

add_executable(test_xcb_image test.c)
target_link_libraries(test_xcb_image PRIVATE xcb-util-image::xcb-util-image)

enable_testing()
add_test(NAME test_xcb_image COMMAND test_xcb_image)
