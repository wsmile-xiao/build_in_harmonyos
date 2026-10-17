cmake_minimum_required(VERSION 3.15)
project(test_s2n_tls C)

# Find the package via Conan-generated CMakeDeps
find_package(s2n-tls REQUIRED)

add_executable(test_s2n_tls test.c)
target_link_libraries(test_s2n_tls s2n-tls::s2n-tls)

enable_testing()
add_test(NAME test_s2n_tls COMMAND test_s2n_tls)
