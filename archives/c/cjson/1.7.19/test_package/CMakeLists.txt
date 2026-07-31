cmake_minimum_required(VERSION 3.5)
project(test_cjson C)

find_package(cjson REQUIRED)

add_executable(test_cjson test_cjson.c)
target_link_libraries(test_cjson PRIVATE cjson::cjson)

enable_testing()
add_test(NAME test_cjson COMMAND test_cjson)