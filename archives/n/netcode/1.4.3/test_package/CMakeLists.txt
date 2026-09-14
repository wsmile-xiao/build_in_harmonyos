cmake_minimum_required(VERSION 3.15)
project(test_netcode C)

# Find the package via Conan-generated CMakeDeps
find_package(netcode REQUIRED)

add_executable(test_netcode test.c)
target_link_libraries(test_netcode netcode::netcode)

enable_testing()
add_test(NAME test_netcode COMMAND test_netcode)
