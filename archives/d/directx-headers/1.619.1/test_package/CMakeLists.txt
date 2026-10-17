cmake_minimum_required(VERSION 3.15)
project(test_directx_headers CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(directx-headers REQUIRED)

add_executable(test_directx_headers test.cpp)
target_link_libraries(test_directx_headers directx-headers::directx-headers)

enable_testing()
add_test(NAME test_directx_headers COMMAND test_directx_headers)
