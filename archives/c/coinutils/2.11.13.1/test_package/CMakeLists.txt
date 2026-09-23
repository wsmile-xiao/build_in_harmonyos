cmake_minimum_required(VERSION 3.15)
project(test_coinutils CXX)

# Find the package via Conan-generated CMakeDeps
find_package(coinutils REQUIRED)

add_executable(test_coinutils test.cpp)
target_link_libraries(test_coinutils coinutils::coinutils)

enable_testing()
add_test(NAME test_coinutils COMMAND test_coinutils)