cmake_minimum_required(VERSION 3.5)
project(test_popt C)

find_package(popt REQUIRED)

add_executable(test_popt test_popt.c)
target_link_libraries(test_popt PRIVATE popt::popt)

enable_testing()
add_test(NAME test_popt COMMAND test_popt)
