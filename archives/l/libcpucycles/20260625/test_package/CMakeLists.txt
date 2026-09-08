cmake_minimum_required(VERSION 3.15)
project(test_cpucycles C)

find_package(libcpucycles REQUIRED)

add_executable(test_cpucycles test.c)
target_link_libraries(test_cpucycles libcpucycles::libcpucycles)

enable_testing()
add_test(NAME test_cpucycles COMMAND test_cpucycles)
