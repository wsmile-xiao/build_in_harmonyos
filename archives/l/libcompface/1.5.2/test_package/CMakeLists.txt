cmake_minimum_required(VERSION 3.15)
project(test_libcompface C)

find_package(libcompface CONFIG REQUIRED)

add_executable(test_libcompface test.c)
target_link_libraries(test_libcompface PRIVATE libcompface::libcompface)

enable_testing()
add_test(NAME test_libcompface COMMAND test_libcompface)
