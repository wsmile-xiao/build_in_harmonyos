cmake_minimum_required(VERSION 3.15)
project(test_unbound C)

find_package(unbound REQUIRED)

add_executable(test_unbound test.c)
target_link_libraries(test_unbound unbound::unbound)

enable_testing()
add_test(NAME test_unbound COMMAND test_unbound)
