cmake_minimum_required(VERSION 3.15)
project(test_liboauth2 C)

find_package(liboauth2 REQUIRED)

add_executable(test_liboauth2 test.c)
target_link_libraries(test_liboauth2 liboauth2::liboauth2)

enable_testing()
add_test(NAME test_liboauth2 COMMAND test_liboauth2)
