cmake_minimum_required(VERSION 3.16)
project(test_ayatana_common C)

find_package(ayatana-common REQUIRED CONFIG)

add_executable(test_ayatana_common test.c)
target_link_libraries(test_ayatana_common PRIVATE ayatana-common::ayatana-common)

enable_testing()
add_test(NAME test_ayatana_common COMMAND test_ayatana_common)
