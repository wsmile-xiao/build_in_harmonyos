cmake_minimum_required(VERSION 3.15)
project(test_qqwing CXX)

find_package(qqwing REQUIRED)

add_executable(test_qqwing test.cpp)
target_link_libraries(test_qqwing qqwing::qqwing)

enable_testing()
add_test(NAME test_qqwing COMMAND test_qqwing)
