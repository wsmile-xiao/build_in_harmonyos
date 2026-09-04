cmake_minimum_required(VERSION 3.15)
project(test_bitflags CXX)

# Find the package via Conan-generated CMakeDeps
find_package(bitflags REQUIRED)

add_executable(test_bitflags test_package.cpp)
target_link_libraries(test_bitflags bitflags::bitflags)

enable_testing()
add_test(NAME test_bitflags COMMAND test_bitflags)