cmake_minimum_required(VERSION 3.15)
project(test_multicast-relay C)

# Find the package via Conan-generated CMakeDeps
find_package(multicast-relay REQUIRED)

add_executable(test_multicast-relay test.c)
target_link_libraries(test_multicast-relay multicast-relay::multicast-relay)

enable_testing()
add_test(NAME test_multicast-relay COMMAND test_multicast-relay)
