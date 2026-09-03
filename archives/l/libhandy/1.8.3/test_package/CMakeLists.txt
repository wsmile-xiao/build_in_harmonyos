cmake_minimum_required(VERSION 3.15)
project(test_libhandy C)

find_package(libhandy REQUIRED CONFIG)

add_executable(test_libhandy test.c)
target_link_libraries(test_libhandy PRIVATE libhandy::libhandy)

enable_testing()
add_test(NAME test_libhandy COMMAND test_libhandy)
