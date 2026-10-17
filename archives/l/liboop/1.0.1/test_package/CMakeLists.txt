cmake_minimum_required(VERSION 3.15)
project(test_liboop C)

find_package(liboop REQUIRED)

add_executable(test_liboop test_liboop.c)
target_link_libraries(test_liboop liboop::liboop)

enable_testing()
add_test(NAME test_liboop COMMAND test_liboop)
