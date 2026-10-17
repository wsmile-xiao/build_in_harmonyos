cmake_minimum_required(VERSION 3.15)
project(test_cadical LANGUAGES C CXX)

find_package(cadical REQUIRED CONFIG)

add_executable(test_cadical test.c)
target_link_libraries(test_cadical PRIVATE cadical::cadical)
set_target_properties(test_cadical PROPERTIES LINKER_LANGUAGE CXX)

enable_testing()
add_test(NAME test_cadical COMMAND test_cadical)
