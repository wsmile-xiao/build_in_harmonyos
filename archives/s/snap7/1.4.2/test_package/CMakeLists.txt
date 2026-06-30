cmake_minimum_required(VERSION 3.15)
project(test_snap7 C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(snap7 REQUIRED)

add_executable(test_snap7 test.cpp)
target_link_libraries(test_snap7 snap7::snap7)

enable_testing()
add_test(NAME test_snap7 COMMAND test_snap7)
