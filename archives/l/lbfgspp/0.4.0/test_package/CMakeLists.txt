cmake_minimum_required(VERSION 3.15)
project(test_lbfgspp CXX)

find_package(lbfgspp REQUIRED)

add_executable(test_lbfgspp test.cpp)
target_link_libraries(test_lbfgspp PRIVATE lbfgspp::lbfgspp)
set_property(TARGET test_lbfgspp PROPERTY CXX_STANDARD 17)
set_property(TARGET test_lbfgspp PROPERTY CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_lbfgspp COMMAND test_lbfgspp)
