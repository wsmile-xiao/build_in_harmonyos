cmake_minimum_required(VERSION 3.15)
project(test_nameof CXX)

# Find the package via Conan-generated CMakeDeps
find_package(nameof REQUIRED)

add_executable(test_nameof test.cpp)
target_link_libraries(test_nameof nameof::nameof)
set_target_properties(test_nameof PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_nameof COMMAND test_nameof)
