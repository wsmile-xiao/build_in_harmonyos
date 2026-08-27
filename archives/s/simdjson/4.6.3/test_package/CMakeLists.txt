cmake_minimum_required(VERSION 3.15)
project(test_simdjson CXX)

find_package(simdjson REQUIRED)

add_executable(test_simdjson test.cpp)
target_link_libraries(test_simdjson simdjson::simdjson)

enable_testing()
add_test(NAME test_simdjson COMMAND test_simdjson)
