cmake_minimum_required(VERSION 3.15)
project(ruli_test_package C)

find_package(ruli REQUIRED CONFIG)

add_executable(test_ruli test_ruli.c)
target_link_libraries(test_ruli PRIVATE ruli::ruli)
