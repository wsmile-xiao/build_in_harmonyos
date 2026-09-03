cmake_minimum_required(VERSION 3.15)
project(test_meshoptimizer CXX)

# Find the package via Conan-generated CMakeDeps
find_package(meshoptimizer REQUIRED)

add_executable(test_meshoptimizer test.cpp)
target_link_libraries(test_meshoptimizer meshoptimizer::meshoptimizer)

enable_testing()
add_test(NAME test_meshoptimizer COMMAND test_meshoptimizer)
