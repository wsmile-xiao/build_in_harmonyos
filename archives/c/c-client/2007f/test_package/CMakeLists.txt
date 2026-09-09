cmake_minimum_required(VERSION 3.15)
project(test_cclient C)

find_package(c-client REQUIRED)

add_executable(test_cclient test.c)
target_link_libraries(test_cclient PRIVATE c-client::c-client)
