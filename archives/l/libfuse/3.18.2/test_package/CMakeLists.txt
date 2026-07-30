cmake_minimum_required(VERSION 3.15)
project(test_libfuse C)

# Find the package via Conan-generated CMakeDeps
find_package(libfuse REQUIRED)

add_executable(test_libfuse test.c)
# libfuse Conan package creates libfuse::libfuse target (CMakeDeps)
target_link_libraries(test_libfuse libfuse::libfuse)

enable_testing()
add_test(NAME test_libfuse COMMAND test_libfuse)
