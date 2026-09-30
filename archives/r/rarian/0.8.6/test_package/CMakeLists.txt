cmake_minimum_required(VERSION 3.15)
project(test_rarian C)

find_package(rarian REQUIRED)

add_executable(test_rarian test_rarian.c)
target_link_libraries(test_rarian rarian::rarian)

enable_testing()
add_test(NAME test_rarian COMMAND test_rarian)
