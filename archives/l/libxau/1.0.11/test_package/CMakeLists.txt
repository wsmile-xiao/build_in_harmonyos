cmake_minimum_required(VERSION 3.15)
project(test_libxau C)

find_package(libxau REQUIRED)

add_executable(test_libxau test.c)
target_link_libraries(test_libxau PRIVATE libxau::libxau)

enable_testing()
add_test(NAME test_libxau COMMAND test_libxau)