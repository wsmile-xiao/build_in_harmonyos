cmake_minimum_required(VERSION 3.15)
project(test_libxutils C)

# Find the package via Conan-generated CMakeDeps
find_package(libxutils REQUIRED)

add_executable(test_libxutils test.c)
target_link_libraries(test_libxutils libxutils::libxutils)

enable_testing()
add_test(NAME test_libxutils COMMAND test_libxutils)
