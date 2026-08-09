cmake_minimum_required(VERSION 3.15)
project(acf_lib_lua55_test LANGUAGES C)

find_package(lua REQUIRED CONFIG)

add_executable(acf_lib_probe acf_lib_probe.c)
target_link_libraries(acf_lib_probe PRIVATE lua::lua)
