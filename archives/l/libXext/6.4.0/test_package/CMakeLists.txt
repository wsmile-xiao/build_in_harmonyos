cmake_minimum_required(VERSION 3.15)
project(test_libxext C)

find_package(libxext REQUIRED)

add_executable(test_libxext test.c)
target_link_libraries(test_libxext PRIVATE libxext::libxext)

enable_testing()
add_test(NAME test_libxext COMMAND test_libxext)
