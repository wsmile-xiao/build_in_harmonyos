cmake_minimum_required(VERSION 3.15)
project(test_t1ha C)

find_package(t1ha REQUIRED)

add_executable(test_t1ha test_t1ha.c)
target_link_libraries(test_t1ha t1ha::t1ha)

enable_testing()
add_test(NAME test_t1ha COMMAND test_t1ha)
