cmake_minimum_required(VERSION 3.15)
project(test_kitemviews CXX)

find_package(KF6ItemViews REQUIRED)

add_executable(test_kitemviews test.cpp)
target_link_libraries(test_kitemviews KF6::ItemViews)

enable_testing()
add_test(NAME test_kitemviews COMMAND test_kitemviews)
