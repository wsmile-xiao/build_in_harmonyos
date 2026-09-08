cmake_minimum_required(VERSION 3.15)
project(test_libmatio C)

find_package(matio REQUIRED)

add_executable(test_libmatio test_libmatio.c)
target_link_libraries(test_libmatio matio::matio)

enable_testing()
add_test(NAME test_libmatio COMMAND test_libmatio)
