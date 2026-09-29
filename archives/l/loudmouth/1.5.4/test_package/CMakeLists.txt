cmake_minimum_required(VERSION 3.15)
project(test_loudmouth C)

find_package(loudmouth REQUIRED)

add_executable(test_loudmouth test.c)
target_link_libraries(test_loudmouth PRIVATE loudmouth::loudmouth)

enable_testing()
add_test(NAME test_loudmouth COMMAND test_loudmouth)
