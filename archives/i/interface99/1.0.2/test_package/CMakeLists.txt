cmake_minimum_required(VERSION 3.15)
project(test_interface99 C)

find_package(interface99 REQUIRED)

add_executable(test_interface99 test_interface99.c)
target_link_libraries(test_interface99 PRIVATE interface99::interface99)
set_target_properties(test_interface99 PROPERTIES
    C_STANDARD 99 C_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME interface99_consumer COMMAND test_interface99)
