cmake_minimum_required(VERSION 3.15)
project(test_libgpiod C)

# Find the package via Conan-generated CMakeDeps
find_package(libgpiod REQUIRED)

add_executable(test_libgpiod test.c)
target_link_libraries(test_libgpiod libgpiod::libgpiod)

enable_testing()
add_test(NAME test_libgpiod COMMAND test_libgpiod)
