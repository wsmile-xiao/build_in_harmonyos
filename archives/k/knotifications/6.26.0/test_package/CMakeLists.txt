cmake_minimum_required(VERSION 3.15)
project(test_knotifications CXX)

find_package(KF6Notifications REQUIRED)

add_executable(test_knotifications test.cpp)
target_link_libraries(test_knotifications KF6::Notifications)

enable_testing()
add_test(NAME test_knotifications COMMAND test_knotifications)
