cmake_minimum_required(VERSION 3.15)
project(test_libfdt C)

find_package(libfdt REQUIRED)

add_executable(test_libfdt test_libfdt.c)
target_link_libraries(test_libfdt libfdt::libfdt)

enable_testing()
add_test(NAME test_libfdt COMMAND test_libfdt)
