cmake_minimum_required(VERSION 3.15)
project(test_libffi C)

# Find the package via Conan-generated CMakeDeps
find_package(libffi REQUIRED)

add_executable(test_libffi test.c)
target_link_libraries(test_libffi libffi::libffi)

enable_testing()
add_test(NAME test_libffi COMMAND test_libffi)
