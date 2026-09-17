cmake_minimum_required(VERSION 3.15)
project(test_liblastlog2 C)

find_package(lastlog2 CONFIG REQUIRED)

add_executable(test_lastlog2_consumer test.c)
target_link_libraries(test_lastlog2_consumer PRIVATE lastlog2::lastlog2)

enable_testing()
add_test(NAME test_lastlog2_consumer COMMAND test_lastlog2_consumer)
