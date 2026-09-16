cmake_minimum_required(VERSION 3.15)
project(test_libcaca C)

find_package(libcaca REQUIRED)

add_executable(test_libcaca test_libcaca.c)
target_link_libraries(test_libcaca PRIVATE libcaca::caca)

enable_testing()
add_test(NAME test_libcaca COMMAND test_libcaca)
