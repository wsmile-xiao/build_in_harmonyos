cmake_minimum_required(VERSION 3.15)
project(test_libbfio C)

# Find the package via Conan-generated CMakeDeps
find_package(libbfio REQUIRED)

add_executable(test_libbfio test.c)
target_link_libraries(test_libbfio libbfio::libbfio)

enable_testing()
add_test(NAME test_libbfio COMMAND test_libbfio)
