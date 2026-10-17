cmake_minimum_required(VERSION 3.15)
project(test_xlsxio C)

find_package(xlsxio REQUIRED CONFIG)

add_executable(test_xlsxio test_xlsxio.c)
target_link_libraries(test_xlsxio PRIVATE xlsxio::xlsxio)

enable_testing()
add_test(NAME xlsxio_consumer COMMAND test_xlsxio)
