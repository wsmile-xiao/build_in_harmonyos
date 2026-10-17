cmake_minimum_required(VERSION 3.15)
project(test_gnutls C)

# Find the package via Conan-generated CMakeDeps
find_package(gnutls REQUIRED)

add_executable(test_gnutls test.c)
target_link_libraries(test_gnutls gnutls::gnutls)

enable_testing()
add_test(NAME test_gnutls COMMAND test_gnutls)
