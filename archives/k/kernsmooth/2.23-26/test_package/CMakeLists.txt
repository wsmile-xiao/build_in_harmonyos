cmake_minimum_required(VERSION 3.15)
project(test_kernsmooth C)

find_package(kernsmooth REQUIRED)

add_executable(test_kernsmooth test_kernsmooth.c)
target_link_libraries(test_kernsmooth kernsmooth::kernsmooth)

enable_testing()
add_test(NAME test_kernsmooth COMMAND test_kernsmooth)