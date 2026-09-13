cmake_minimum_required(VERSION 3.16)
project(test_cauchy CXX)

enable_testing()

find_package(cauchy REQUIRED)

add_executable(test_cauchy src/test_cauchy.cpp)
target_link_libraries(test_cauchy cauchy::cauchy)
add_test(NAME cauchy_version COMMAND test_cauchy)
