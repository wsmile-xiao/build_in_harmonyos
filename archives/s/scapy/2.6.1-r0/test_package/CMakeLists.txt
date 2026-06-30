cmake_minimum_required(VERSION 3.15)
project(test_scapy C)

# Find the package via Conan-generated CMakeDeps
find_package(scapy REQUIRED)

add_executable(test_scapy test.c)
target_link_libraries(test_scapy scapy::scapy)

enable_testing()
add_test(NAME test_scapy COMMAND test_scapy)
