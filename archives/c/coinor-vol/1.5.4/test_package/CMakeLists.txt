cmake_minimum_required(VERSION 3.15)
project(test_coinor-vol CXX)

# Find the package via Conan-generated CMakeDeps
find_package(coinor-vol REQUIRED)

add_executable(test_coinor-vol test.cpp)
target_link_libraries(test_coinor-vol coinor-vol::coinor-vol)

enable_testing()
add_test(NAME test_coinor-vol COMMAND test_coinor-vol)