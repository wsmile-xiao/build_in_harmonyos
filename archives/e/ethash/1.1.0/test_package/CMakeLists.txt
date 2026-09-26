cmake_minimum_required(VERSION 3.15)
project(test_ethash CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ethash REQUIRED)

add_executable(test_ethash test.cpp)
target_link_libraries(test_ethash ethash::ethash)

enable_testing()
add_test(NAME test_ethash COMMAND test_ethash)
