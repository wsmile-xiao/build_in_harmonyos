cmake_minimum_required(VERSION 3.15)
project(test_kernel_headers C)

find_package(kernel-headers REQUIRED)

add_executable(test_kernel_headers test_kernel_headers.c)
target_link_libraries(test_kernel_headers PRIVATE kernel-headers::kernel-headers)
