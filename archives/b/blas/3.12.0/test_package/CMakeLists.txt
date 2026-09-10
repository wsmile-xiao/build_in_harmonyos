cmake_minimum_required(VERSION 3.15)
project(blas_test C)

find_package(blas REQUIRED CONFIG)

add_executable(test_blas test.c)
target_link_libraries(test_blas PRIVATE blas::blas)

enable_testing()
add_test(NAME test_blas COMMAND test_blas)
