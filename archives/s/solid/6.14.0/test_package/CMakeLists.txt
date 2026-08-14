cmake_minimum_required(VERSION 3.15)
project(test_solid CXX)

find_package(KF6Solid REQUIRED)

add_executable(test_solid test.cpp)
target_link_libraries(test_solid KF6::Solid)

enable_testing()
add_test(NAME test_solid COMMAND test_solid)
