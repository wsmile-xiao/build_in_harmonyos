cmake_minimum_required(VERSION 3.15)
project(test_libxmi C)

# Find the package via Conan-generated CMakeDeps
find_package(libxmi REQUIRED)

add_executable(test_libxmi test.c)
target_link_libraries(test_libxmi libxmi::libxmi)

enable_testing()
add_test(NAME test_libxmi COMMAND test_libxmi)
