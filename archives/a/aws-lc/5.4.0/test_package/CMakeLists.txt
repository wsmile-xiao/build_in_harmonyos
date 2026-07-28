cmake_minimum_required(VERSION 3.15)
project(test_aws-lc C)

# Find the package via Conan-generated CMakeDeps
find_package(aws-lc REQUIRED)

add_executable(test_aws-lc test.c)
target_link_libraries(test_aws-lc aws-lc::aws-lc)

enable_testing()
add_test(NAME test_aws-lc COMMAND test_aws-lc)
