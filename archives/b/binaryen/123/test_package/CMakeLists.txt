cmake_minimum_required(VERSION 3.15)
project(test_binaryen CXX)

add_executable(test_binaryen test.cpp)

enable_testing()
add_test(NAME test_binaryen COMMAND test_binaryen)
