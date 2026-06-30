cmake_minimum_required(VERSION 3.15)
project(test_unudhcpd C)

# Find the package via Conan-generated CMakeDeps
find_package(unudhcpd REQUIRED)

add_executable(test_unudhcpd test.c)
target_link_libraries(test_unudhcpd unudhcpd::unudhcpd)

enable_testing()
add_test(NAME test_unudhcpd COMMAND test_unudhcpd)
