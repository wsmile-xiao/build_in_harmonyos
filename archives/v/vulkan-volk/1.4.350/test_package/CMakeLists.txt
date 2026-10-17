cmake_minimum_required(VERSION 3.15)
project(test_volk C)

# Find the package via Conan-generated CMakeDeps
find_package(volk REQUIRED)

add_executable(test_volk test.c)
target_link_libraries(test_volk volk::volk)

enable_testing()
add_test(NAME test_volk COMMAND test_volk)
