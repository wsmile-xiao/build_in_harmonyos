cmake_minimum_required(VERSION 3.15)
project(test_fcft C)

find_package(fcft REQUIRED)

add_executable(test_fcft test_fcft.c)
target_link_libraries(test_fcft fcft::fcft)

enable_testing()
add_test(NAME test_fcft COMMAND test_fcft)
