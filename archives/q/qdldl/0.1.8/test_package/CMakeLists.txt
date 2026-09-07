cmake_minimum_required(VERSION 3.15)
project(test_qdldl C)

# Find the package via Conan-generated CMakeDeps
find_package(qdldl REQUIRED)

add_executable(test_qdldl test.c)
target_link_libraries(test_qdldl qdldl::qdldl)

enable_testing()
add_test(NAME test_qdldl COMMAND test_qdldl)
