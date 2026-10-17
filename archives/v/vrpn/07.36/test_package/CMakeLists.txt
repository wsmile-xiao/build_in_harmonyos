cmake_minimum_required(VERSION 3.15)
project(test_vrpn CXX)

find_package(vrpn REQUIRED)

add_executable(test_vrpn test.cpp)
target_link_libraries(test_vrpn vrpn::vrpn)

enable_testing()
add_test(NAME test_vrpn COMMAND test_vrpn)
