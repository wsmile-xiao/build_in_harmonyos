cmake_minimum_required(VERSION 3.15)
project(test_libad9361 C)

find_package(libad9361-iio REQUIRED CONFIG)

add_executable(test_libad9361 test_libad9361.c)
target_link_libraries(test_libad9361 PRIVATE libad9361-iio::libad9361-iio)
