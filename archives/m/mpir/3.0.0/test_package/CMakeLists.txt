cmake_minimum_required(VERSION 3.15)
project(test_mpir CXX)

find_package(mpir REQUIRED)

add_executable(test_mpir test.cpp)
target_link_libraries(test_mpir mpir::mpir)

enable_testing()
add_test(NAME test_mpir COMMAND test_mpir)
