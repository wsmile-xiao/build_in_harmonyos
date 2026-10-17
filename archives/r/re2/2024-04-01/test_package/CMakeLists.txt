cmake_minimum_required(VERSION 3.15)
project(test_re2 CXX)

find_package(re2 REQUIRED)

add_executable(test_re2 test.cpp)
target_link_libraries(test_re2 re2::re2)

enable_testing()
add_test(NAME test_re2 COMMAND test_re2)
