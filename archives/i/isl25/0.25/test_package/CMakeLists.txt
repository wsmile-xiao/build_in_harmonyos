cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(isl25 CONFIG REQUIRED)

add_executable(test_isl test.c)
target_link_libraries(test_isl PRIVATE isl25::isl25)

enable_testing()
add_test(NAME test_isl COMMAND test_isl)
