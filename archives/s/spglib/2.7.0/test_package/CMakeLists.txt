cmake_minimum_required(VERSION 3.15)
project(test_spglib C)

find_package(Spglib REQUIRED)

add_executable(test_spglib test.c)
target_link_libraries(test_spglib PRIVATE Spglib::symspg)

enable_testing()
add_test(NAME test_spglib COMMAND test_spglib)
