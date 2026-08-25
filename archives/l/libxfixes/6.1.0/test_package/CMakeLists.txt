cmake_minimum_required(VERSION 3.15)
project(test_libxfixes C)

find_package(libxfixes REQUIRED)

add_executable(test_libxfixes test.c)
target_link_libraries(test_libxfixes PRIVATE libxfixes::libxfixes)

enable_testing()
add_test(NAME test_libxfixes COMMAND test_libxfixes)
