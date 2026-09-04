cmake_minimum_required(VERSION 3.15)
project(test_libstrophe C)

# Find the package via Conan-generated CMakeDeps
find_package(libstrophe REQUIRED)

add_executable(test_libstrophe test.c)
target_link_libraries(test_libstrophe libstrophe::libstrophe)

enable_testing()
add_test(NAME test_libstrophe COMMAND test_libstrophe)
