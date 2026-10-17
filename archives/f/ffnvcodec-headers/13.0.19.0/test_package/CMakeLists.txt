cmake_minimum_required(VERSION 3.15)
project(test_ffnvcodec_headers C)

# Find the package via Conan-generated CMakeDeps
find_package(ffnvcodec-headers REQUIRED)

add_executable(test_ffnvcodec_headers test.c)
target_link_libraries(test_ffnvcodec_headers ffnvcodec-headers::ffnvcodec-headers)

enable_testing()
add_test(NAME test_ffnvcodec_headers COMMAND test_ffnvcodec_headers)
