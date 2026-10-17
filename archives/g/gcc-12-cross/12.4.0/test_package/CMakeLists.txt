cmake_minimum_required(VERSION 3.15)
project(test_gcc-12-cross C)

# Find the package via Conan-generated CMakeDeps
find_package(gcc-12-cross REQUIRED)

add_executable(test_gcc-12-cross test.c)
target_link_libraries(test_gcc-12-cross gcc-12-cross::gcc-12-cross)

enable_testing()
add_test(NAME test_gcc-12-cross COMMAND test_gcc-12-cross)
