cmake_minimum_required(VERSION 3.15)
project(test_skalibs LANGUAGES C)

find_package(skalibs CONFIG REQUIRED)

add_executable(test_skalibs test.c)
target_link_libraries(test_skalibs PRIVATE skalibs::skalibs)

enable_testing()
add_test(NAME test_skalibs COMMAND test_skalibs)
