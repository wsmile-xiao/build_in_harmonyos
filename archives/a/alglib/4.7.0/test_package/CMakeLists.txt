cmake_minimum_required(VERSION 3.15)
project(test_alglib CXX)

find_package(alglib REQUIRED CONFIG)

add_executable(test_alglib test_alglib.cpp)
target_link_libraries(test_alglib PRIVATE alglib::alglib)

enable_testing()
add_test(NAME test_alglib COMMAND test_alglib)
