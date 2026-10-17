cmake_minimum_required(VERSION 3.15)
project(test_ips4o CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(ips4o REQUIRED)

add_executable(test_ips4o test.cpp)
target_link_libraries(test_ips4o ips4o::ips4o)

enable_testing()
add_test(NAME test_ips4o COMMAND test_ips4o)