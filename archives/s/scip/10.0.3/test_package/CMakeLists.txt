cmake_minimum_required(VERSION 3.15)
project(test_scip C)

find_package(scip REQUIRED)

add_executable(test_scip test_scip.c)
target_link_libraries(test_scip scip::scip)

enable_testing()
add_test(NAME test_scip COMMAND test_scip)
