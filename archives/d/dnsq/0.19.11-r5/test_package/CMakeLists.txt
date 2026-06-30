cmake_minimum_required(VERSION 3.15)
project(test_dnsq C)

# Find the package via Conan-generated CMakeDeps
find_package(dnsq REQUIRED)

add_executable(test_dnsq test.c)
target_link_libraries(test_dnsq dnsq::dnsq)

enable_testing()
add_test(NAME test_dnsq COMMAND test_dnsq)
