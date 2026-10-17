cmake_minimum_required(VERSION 3.15)
project(test_criterion C)

find_package(criterion REQUIRED)

add_executable(test_criterion test.c)
target_link_libraries(test_criterion criterion::criterion)

enable_testing()
add_test(NAME test_criterion COMMAND test_criterion)
