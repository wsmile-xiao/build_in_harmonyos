cmake_minimum_required(VERSION 3.12)
project(test_json_c C)

include(CTest)

find_package(json-c REQUIRED CONFIG)

add_executable(test_json_c test.c)
target_link_libraries(test_json_c PRIVATE json-c::json-c)

add_test(NAME json_c_version COMMAND test_json_c)