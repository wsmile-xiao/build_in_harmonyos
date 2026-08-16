cmake_minimum_required(VERSION 3.15)
project(test_dhcpstarv C)

# Find the package via Conan-generated CMakeDeps
find_package(dhcpstarv REQUIRED)

add_executable(test_dhcpstarv test.c)
target_link_libraries(test_dhcpstarv dhcpstarv::dhcpstarv)

enable_testing()
add_test(NAME test_dhcpstarv COMMAND test_dhcpstarv)
