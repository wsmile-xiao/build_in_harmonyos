cmake_minimum_required(VERSION 3.15)
project(test_libdeflate C)

find_package(libdeflate REQUIRED)

add_executable(test_libdeflate test.c)
target_link_libraries(test_libdeflate libdeflate::libdeflate)

enable_testing()
add_test(NAME test_libdeflate COMMAND test_libdeflate)
