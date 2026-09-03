cmake_minimum_required(VERSION 3.15)
project(test_stringzilla C)

find_package(stringzilla CONFIG REQUIRED)

add_executable(test_stringzilla test.c)
target_link_libraries(test_stringzilla PRIVATE stringzilla::shared)
set_target_properties(test_stringzilla PROPERTIES C_STANDARD 99 C_STANDARD_REQUIRED ON)
