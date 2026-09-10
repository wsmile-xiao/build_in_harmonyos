cmake_minimum_required(VERSION 3.15)
project(test_bcunit C)

find_package(bcunit REQUIRED)

add_executable(test_bcunit test.c)
target_link_libraries(test_bcunit bcunit::bcunit)

enable_testing()
add_test(NAME test_bcunit COMMAND test_bcunit)
