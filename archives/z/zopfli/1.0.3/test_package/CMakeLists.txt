cmake_minimum_required(VERSION 3.15)
project(test_zopfli C)

find_package(zopfli REQUIRED)

add_executable(test_zopfli test.c)
target_link_libraries(test_zopfli zopfli::zopfli)

enable_testing()
add_test(NAME test_zopfli COMMAND test_zopfli)
