cmake_minimum_required(VERSION 3.16)
project(test_libredblack C)

set(CMAKE_C_STANDARD 99)

enable_testing()

find_package(libredblack REQUIRED)

add_executable(test_libredblack src/test_libredblack.c)
target_link_libraries(test_libredblack libredblack::libredblack)

add_test(NAME libredblack_consumer COMMAND test_libredblack)
