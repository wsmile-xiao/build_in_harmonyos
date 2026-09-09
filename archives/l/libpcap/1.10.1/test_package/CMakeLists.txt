cmake_minimum_required(VERSION 3.15)
project(test_libpcap C)

# Find the package via Conan-generated CMakeDeps
find_package(libpcap REQUIRED)

add_executable(test_libpcap test.c)
target_link_libraries(test_libpcap libpcap::libpcap)

enable_testing()
add_test(NAME test_libpcap COMMAND test_libpcap)
