cmake_minimum_required(VERSION 3.15)
project(test_airspy C)

find_package(airspy REQUIRED)

add_executable(test_airspy src/main.c)
target_link_libraries(test_airspy airspy::airspy)

enable_testing()
add_test(NAME test_airspy COMMAND test_airspy)
