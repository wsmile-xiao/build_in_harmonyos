cmake_minimum_required(VERSION 3.15)
project(test_fathom C)

find_package(fathom REQUIRED)

add_executable(test_fathom test_fathom.c)
target_link_libraries(test_fathom fathom::fathom)

enable_testing()
add_test(NAME test_fathom COMMAND test_fathom)
