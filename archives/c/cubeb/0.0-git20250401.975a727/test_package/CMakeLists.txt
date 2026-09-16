cmake_minimum_required(VERSION 3.15)
project(test_cubeb C CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cubeb REQUIRED)

add_executable(test_cubeb test.cpp)
target_link_libraries(test_cubeb cubeb::cubeb)

enable_testing()
add_test(NAME test_cubeb COMMAND test_cubeb)
