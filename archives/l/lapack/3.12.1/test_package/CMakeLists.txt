cmake_minimum_required(VERSION 3.15)
project(lapack_test C)

find_package(lapack REQUIRED)

add_executable(test_lapack test.c)
target_link_libraries(test_lapack PRIVATE lapack::lapack)

enable_testing()
add_test(NAME test_lapack COMMAND test_lapack)
