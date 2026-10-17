cmake_minimum_required(VERSION 3.15)
project(test_libmpd C)

find_package(libmpd REQUIRED)

add_executable(test_libmpd test_libmpd.c)
target_link_libraries(test_libmpd libmpd::libmpd)

enable_testing()
add_test(NAME test_libmpd COMMAND test_libmpd)
