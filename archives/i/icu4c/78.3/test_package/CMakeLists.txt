cmake_minimum_required(VERSION 3.15)
project(test_icu4c CXX)

find_package(icu4c REQUIRED)

add_executable(test_icu4c test_icu4c.cpp)
target_link_libraries(test_icu4c icu4c::icu4c)

enable_testing()
add_test(NAME test_icu4c COMMAND test_icu4c)
