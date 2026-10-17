cmake_minimum_required(VERSION 3.15)
project(test_libcontra C)

find_package(libcontra REQUIRED)

add_executable(test_libcontra test_libcontra.c)
target_link_libraries(test_libcontra libcontra::libcontra)

enable_testing()
add_test(NAME test_libcontra COMMAND test_libcontra)
