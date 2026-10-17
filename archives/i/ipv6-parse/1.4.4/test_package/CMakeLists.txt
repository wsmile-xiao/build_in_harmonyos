cmake_minimum_required(VERSION 3.15)
project(test_ipv6-parse C)

# Find the package via Conan-generated CMakeDeps
find_package(ipv6-parse REQUIRED)

add_executable(test_ipv6-parse test.c)
target_link_libraries(test_ipv6-parse ipv6-parse::ipv6-parse)

enable_testing()
add_test(NAME test_ipv6-parse COMMAND test_ipv6-parse)
