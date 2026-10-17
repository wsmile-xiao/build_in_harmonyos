cmake_minimum_required(VERSION 3.15)
project(test_nemu C)

# Find the package via Conan-generated CMakeDeps
find_package(nemu REQUIRED)

add_executable(test_nemu test.c)
target_link_libraries(test_nemu nemu::nemu)
