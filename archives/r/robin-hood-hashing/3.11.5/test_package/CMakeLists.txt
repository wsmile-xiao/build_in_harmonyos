cmake_minimum_required(VERSION 3.15)
project(test_robin-hood-hashing CXX)

# Find the package via Conan-generated CMakeDeps
find_package(robin_hood REQUIRED)

add_executable(test_robin-hood-hashing test.cpp)
target_link_libraries(test_robin-hood-hashing robin_hood::robin_hood)

enable_testing()
add_test(NAME test_robin-hood-hashing COMMAND test_robin-hood-hashing)
