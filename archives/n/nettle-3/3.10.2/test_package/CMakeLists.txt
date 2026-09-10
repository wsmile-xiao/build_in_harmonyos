cmake_minimum_required(VERSION 3.15)
project(test_nettle C)

# Find the package via Conan-generated CMakeDeps
find_package(nettle-3 REQUIRED)

add_executable(test_nettle test.c)
target_link_libraries(test_nettle nettle-3::nettle-3)

enable_testing()
add_test(NAME test_nettle COMMAND test_nettle)
