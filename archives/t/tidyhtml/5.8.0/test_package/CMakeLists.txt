cmake_minimum_required(VERSION 3.15)
project(test_tidy C)

find_package(Tidy REQUIRED CONFIG)

add_executable(test_tidy test_tidy.c)
target_link_libraries(test_tidy PRIVATE Tidy::Tidy)

enable_testing()
add_test(NAME tidy_test COMMAND test_tidy)
