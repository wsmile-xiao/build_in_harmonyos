cmake_minimum_required(VERSION 3.15)
project(test_keystone CXX)

find_package(keystone REQUIRED)

add_executable(test_keystone test.cpp)
target_link_libraries(test_keystone keystone::keystone)

enable_testing()
add_test(NAME test_keystone COMMAND test_keystone)
