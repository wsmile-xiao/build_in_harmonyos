cmake_minimum_required(VERSION 3.15)
project(openbabel_consumer_test CXX)

find_package(openbabel REQUIRED CONFIG)

add_executable(test_package_exe test.cpp)
target_link_libraries(test_package_exe PRIVATE openbabel::openbabel)
