cmake_minimum_required(VERSION 3.15)
project(test_libngtcp2 C)

# Find the package via Conan-generated CMakeDeps
find_package(libngtcp2 REQUIRED)

add_executable(test_libngtcp2 test.c)
target_link_libraries(test_libngtcp2 libngtcp2::libngtcp2)

enable_testing()
add_test(NAME test_libngtcp2 COMMAND test_libngtcp2)
