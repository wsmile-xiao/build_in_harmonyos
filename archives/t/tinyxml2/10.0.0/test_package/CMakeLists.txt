cmake_minimum_required(VERSION 3.15)
project(test_tinyxml2 CXX)

find_package(tinyxml2 REQUIRED CONFIG)

add_executable(test_tinyxml2 test_tinyxml2.cpp)
target_link_libraries(test_tinyxml2 PRIVATE tinyxml2::tinyxml2)

enable_testing()
add_test(NAME tinyxml2_test COMMAND test_tinyxml2)
