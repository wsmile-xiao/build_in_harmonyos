cmake_minimum_required(VERSION 3.5)
project(test_cctest CXX)

find_package(cctest REQUIRED CONFIG)

add_executable(test_cctest test_cctest.cc)
target_link_libraries(test_cctest PRIVATE cctest::cctest)