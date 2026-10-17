cmake_minimum_required(VERSION 3.15)
project(test_aegis C)

find_package(aegis REQUIRED)

add_executable(test_aegis test.c)
target_link_libraries(test_aegis PRIVATE aegis::aegis)

enable_testing()
add_test(NAME test_aegis COMMAND test_aegis)
