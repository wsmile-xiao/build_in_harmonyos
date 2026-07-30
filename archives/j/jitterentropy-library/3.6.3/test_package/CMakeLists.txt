cmake_minimum_required(VERSION 3.15)
project(test_jitterentropy C)

find_package(jitterentropy-library REQUIRED)

add_executable(test_jitterentropy test.c)
target_link_libraries(test_jitterentropy jitterentropy-library::jitterentropy-library)

enable_testing()
add_test(NAME test_jitterentropy COMMAND test_jitterentropy)
