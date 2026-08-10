cmake_minimum_required(VERSION 3.15)
project(test_opencl_icd_loader C)

find_package(OpenCL REQUIRED)
find_package(opencl-headers REQUIRED)

add_executable(test_opencl_icd_loader test.c)
target_link_libraries(test_opencl_icd_loader OpenCL::OpenCL opencl-headers::opencl-headers)

enable_testing()
add_test(NAME test_opencl_icd_loader COMMAND test_opencl_icd_loader)
