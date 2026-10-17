cmake_minimum_required(VERSION 3.15)
project(test_rocm_hipamd CXX)

find_package(rocm-hipamd REQUIRED)

add_executable(test_package src/test_package.cpp)
target_link_libraries(test_package rocm-hipamd::rocm-hipamd)
# Host-side consumers select the AMD HIP platform variant; required by
# library_types.h (guards on __HIP_PLATFORM_AMD__/__HIP_PLATFORM_NVIDIA__).
target_compile_definitions(test_package PRIVATE __HIP_PLATFORM_AMD__=1)

enable_testing()
add_test(NAME test_package COMMAND test_package)
