cmake_minimum_required(VERSION 3.15)
project(test_aften C)

find_package(aften REQUIRED CONFIG)

add_executable(test_aften test.c)
target_link_libraries(test_aften PRIVATE aften::aften)
