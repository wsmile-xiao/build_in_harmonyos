cmake_minimum_required(VERSION 3.15)
project(test_plplot CXX)

find_package(plplot REQUIRED CONFIG)

add_executable(test_plplot test.cpp)
target_link_libraries(test_plplot PRIVATE plplot::plplot)

enable_testing()
add_test(NAME test_plplot COMMAND test_plplot)
