cmake_minimum_required(VERSION 3.15)
project(test_md4c C)

find_package(md4c REQUIRED)

add_executable(test_md4c test_md4c.c)
target_link_libraries(test_md4c md4c::md4c)

enable_testing()
add_test(NAME test_md4c COMMAND test_md4c)
