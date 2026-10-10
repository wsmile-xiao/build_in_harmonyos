cmake_minimum_required(VERSION 3.15)
project(test_libdazzle C)

# Find the package via Conan-generated CMakeDeps
find_package(libdazzle REQUIRED)

add_executable(test_libdazzle test.c)
target_link_libraries(test_libdazzle libdazzle::libdazzle)

enable_testing()
add_test(NAME test_libdazzle COMMAND test_libdazzle)
