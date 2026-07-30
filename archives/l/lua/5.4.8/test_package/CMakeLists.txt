cmake_minimum_required(VERSION 3.15)
project(test_lua C)

find_package(lua CONFIG REQUIRED)

add_executable(test_lua test_lua.c)
target_link_libraries(test_lua PRIVATE lua::lua)
