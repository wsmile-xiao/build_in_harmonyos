cmake_minimum_required(VERSION 3.15)
project(test_libayatana-common C)

# Find the package via Conan-generated CMakeDeps
find_package(libayatana-common REQUIRED)

add_executable(test_libayatana-common test.c)
target_link_libraries(test_libayatana-common libayatana-common::libayatana-common)

enable_testing()
add_test(NAME test_libayatana-common COMMAND test_libayatana-common)
