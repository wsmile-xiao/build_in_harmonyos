cmake_minimum_required(VERSION 3.15)
project(test_libmodbus C)

# Find the package via Conan-generated CMakeDeps
find_package(libmodbus REQUIRED)

add_executable(test_libmodbus test.c)
target_link_libraries(test_libmodbus libmodbus::libmodbus)

enable_testing()
add_test(NAME test_libmodbus COMMAND test_libmodbus)
