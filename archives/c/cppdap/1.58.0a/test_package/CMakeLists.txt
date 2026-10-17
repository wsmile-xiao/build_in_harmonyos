cmake_minimum_required(VERSION 3.15)
project(test_cppdap CXX)

find_package(cppdap REQUIRED)

add_executable(test_cppdap test_cppdap.cpp)
target_link_libraries(test_cppdap PRIVATE cppdap::cppdap)

enable_testing()
add_test(NAME test_cppdap COMMAND test_cppdap)
