cmake_minimum_required(VERSION 3.15)
project(test_cpptest CXX)

find_package(cpptest CONFIG REQUIRED)

add_executable(test_cpptest test_cpptest.cpp)
target_link_libraries(test_cpptest PRIVATE cpptest::cpptest)

enable_testing()
add_test(NAME cpptest_consumer_suite COMMAND test_cpptest)
