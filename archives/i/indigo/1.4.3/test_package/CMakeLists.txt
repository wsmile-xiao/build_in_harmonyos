cmake_minimum_required(VERSION 3.15)
project(indigo_test C)

find_package(indigo CONFIG REQUIRED)

add_executable(test_indigo test_indigo.c)
target_link_libraries(test_indigo PRIVATE indigo::indigo)
enable_testing()
add_test(NAME test_indigo COMMAND test_indigo)
