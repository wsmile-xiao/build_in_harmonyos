cmake_minimum_required(VERSION 3.15)
project(test_lldpd C)

find_package(lldpd REQUIRED)

add_executable(test_lldpd test.c)
target_link_libraries(test_lldpd lldpd::lldpd)

enable_testing()
add_test(NAME test_lldpd COMMAND test_lldpd)
