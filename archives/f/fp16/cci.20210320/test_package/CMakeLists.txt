cmake_minimum_required(VERSION 3.15)
project(test_fp16 C)

# Find the package via Conan-generated CMakeDeps
find_package(fp16 REQUIRED)

add_executable(test_fp16 test.c)
target_link_libraries(test_fp16 fp16::fp16)

enable_testing()
add_test(NAME test_fp16 COMMAND test_fp16)
