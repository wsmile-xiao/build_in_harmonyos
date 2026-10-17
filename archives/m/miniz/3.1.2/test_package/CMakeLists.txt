cmake_minimum_required(VERSION 3.15)
project(test_miniz C)

# Find the package via Conan-generated CMakeDeps
find_package(miniz REQUIRED)

add_executable(test_miniz test.c)
target_link_libraries(test_miniz miniz::miniz)

enable_testing()
add_test(NAME test_miniz COMMAND test_miniz)
