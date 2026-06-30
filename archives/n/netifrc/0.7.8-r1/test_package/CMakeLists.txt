cmake_minimum_required(VERSION 3.15)
project(test_netifrc C)

# Find the package via Conan-generated CMakeDeps
find_package(netifrc REQUIRED)

add_executable(test_netifrc test.c)
target_link_libraries(test_netifrc netifrc::netifrc)

enable_testing()
add_test(NAME test_netifrc COMMAND test_netifrc)
