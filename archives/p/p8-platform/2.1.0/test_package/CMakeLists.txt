cmake_minimum_required(VERSION 3.15)
project(test_p8_platform CXX)

# Find the package via Conan-generated CMakeDeps
find_package(p8-platform REQUIRED)

add_executable(test_p8_platform test.cpp)
target_link_libraries(test_p8_platform p8-platform::p8-platform)

enable_testing()
add_test(NAME test_p8_platform COMMAND test_p8_platform)
