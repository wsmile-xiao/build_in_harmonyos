cmake_minimum_required(VERSION 3.15)
project(test_lrcalc C)

find_package(lrcalc REQUIRED CONFIG)

add_executable(test_lrcalc test.c)
target_link_libraries(test_lrcalc PRIVATE lrcalc::lrcalc)

enable_testing()
add_test(NAME lrcalc_api COMMAND test_lrcalc)
set_tests_properties(lrcalc_api PROPERTIES PASS_REGULAR_EXPRESSION "ALL_OK")
