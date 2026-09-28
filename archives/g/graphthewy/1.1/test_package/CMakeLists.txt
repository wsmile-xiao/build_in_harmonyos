cmake_minimum_required(VERSION 3.15)
project(test_graphthewy CXX)

# Find the package via Conan-generated CMakeDeps
find_package(graphthewy REQUIRED)

add_executable(test_graphthewy test.cpp)
target_link_libraries(test_graphthewy graphthewy::graphthewy)

enable_testing()
add_test(NAME test_graphthewy COMMAND test_graphthewy)