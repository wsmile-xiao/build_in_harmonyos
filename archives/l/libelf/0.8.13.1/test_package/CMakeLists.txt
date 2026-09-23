cmake_minimum_required(VERSION 3.15)
project(test_libelf C)

find_package(libelf REQUIRED)

add_executable(test_libelf test.c)
target_link_libraries(test_libelf libelf::libelf)

enable_testing()
add_test(NAME test_libelf COMMAND test_libelf)
