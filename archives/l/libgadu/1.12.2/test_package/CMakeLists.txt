cmake_minimum_required(VERSION 3.15)
project(test_libgadu C)

find_package(libgadu REQUIRED)

add_executable(test_libgadu test.c)
target_link_libraries(test_libgadu libgadu::libgadu)

enable_testing()
add_test(NAME test_libgadu COMMAND test_libgadu)
