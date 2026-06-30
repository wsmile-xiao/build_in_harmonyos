cmake_minimum_required(VERSION 3.15)
project(test_vouch-proxy C)

# Find the package via Conan-generated CMakeDeps
find_package(vouch-proxy REQUIRED)

add_executable(test_vouch-proxy test.c)
target_link_libraries(test_vouch-proxy vouch-proxy::vouch-proxy)

enable_testing()
add_test(NAME test_vouch-proxy COMMAND test_vouch-proxy)
