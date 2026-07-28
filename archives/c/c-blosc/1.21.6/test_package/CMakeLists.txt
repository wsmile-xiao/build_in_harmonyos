cmake_minimum_required(VERSION 3.15)
project(test_c_blosc C)

find_package(c-blosc REQUIRED)

add_executable(test_c_blosc test.c)
target_link_libraries(test_c_blosc c-blosc::c-blosc)

enable_testing()
add_test(NAME test_c_blosc COMMAND test_c_blosc)
