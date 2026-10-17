cmake_minimum_required(VERSION 3.15)
project(test_flatcv C)

find_package(flatcv REQUIRED CONFIG)

add_executable(test_flatcv test_package.c)
target_link_libraries(test_flatcv flatcv::flatcv)

enable_testing()
add_test(NAME test_flatcv COMMAND test_flatcv)
