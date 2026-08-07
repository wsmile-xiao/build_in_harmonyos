cmake_minimum_required(VERSION 3.15)
project(test_libssh C)

# Find the package via Conan-generated CMakeDeps
find_package(libssh REQUIRED)

add_executable(test_libssh test.c)
target_link_libraries(test_libssh libssh::libssh)

enable_testing()
add_test(NAME test_libssh COMMAND test_libssh)
