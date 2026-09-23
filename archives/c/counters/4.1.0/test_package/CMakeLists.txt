cmake_minimum_required(VERSION 3.15)
project(test_counters CXX)

find_package(Counters CONFIG REQUIRED)
add_executable(test_counters test.cpp)
target_link_libraries(test_counters PRIVATE Counters::counters)

enable_testing()
add_test(NAME test_counters COMMAND test_counters)
