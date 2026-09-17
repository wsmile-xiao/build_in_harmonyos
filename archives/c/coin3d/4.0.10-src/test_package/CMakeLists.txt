cmake_minimum_required(VERSION 3.15)
project(test_coin3d CXX)

find_package(coin3d REQUIRED)

add_executable(test_coin3d test.cpp)
target_link_libraries(test_coin3d coin3d::coin3d)

enable_testing()
add_test(NAME test_coin3d COMMAND test_coin3d)
