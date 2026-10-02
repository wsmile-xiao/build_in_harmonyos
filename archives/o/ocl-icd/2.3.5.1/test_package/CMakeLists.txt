cmake_minimum_required(VERSION 3.15)
project(test_ocl_icd C)

find_package(OpenCL REQUIRED)
find_package(opencl-headers REQUIRED)

add_executable(test_ocl_icd test.c)
target_link_libraries(test_ocl_icd OpenCL::OpenCL opencl-headers::opencl-headers)

enable_testing()
add_test(NAME test_ocl_icd COMMAND test_ocl_icd)
