cmake_minimum_required(VERSION 3.15)
project(test_aws_crt_cpp CXX)

set(CMAKE_CXX_STANDARD 11)

# Find the package via Conan-generated CMakeDeps
find_package(aws-crt-cpp REQUIRED)

add_executable(test_aws_crt_cpp test.cpp)
target_link_libraries(test_aws_crt_cpp aws-crt-cpp::aws-crt-cpp)

enable_testing()
add_test(NAME test_aws_crt_cpp COMMAND test_aws_crt_cpp)
