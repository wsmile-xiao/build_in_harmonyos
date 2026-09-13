cmake_minimum_required(VERSION 3.15)
project(test_colpack CXX)

# Find the package via Conan-generated CMakeDeps
find_package(colpack REQUIRED)

add_executable(test_colpack test.cpp)
target_link_libraries(test_colpack PRIVATE colpack::colpack)

enable_testing()
add_test(NAME test_colpack COMMAND test_colpack)
