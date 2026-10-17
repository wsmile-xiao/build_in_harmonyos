cmake_minimum_required(VERSION 3.15)
project(test_libdivsufsort C)

# Find both components via Conan-generated CMakeDeps
find_package(libdivsufsort REQUIRED)

add_executable(test_divsufsort test.c)
target_link_libraries(test_divsufsort PRIVATE
    divsufsort::divsufsort
    divsufsort64::divsufsort64
)

