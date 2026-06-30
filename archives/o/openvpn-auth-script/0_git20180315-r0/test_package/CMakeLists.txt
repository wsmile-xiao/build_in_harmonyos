cmake_minimum_required(VERSION 3.15)
project(test_openvpn-auth-script C)

# Find the package via Conan-generated CMakeDeps
find_package(openvpn-auth-script REQUIRED)

add_executable(test_openvpn-auth-script test.c)
target_link_libraries(test_openvpn-auth-script openvpn-auth-script::openvpn-auth-script)

enable_testing()
add_test(NAME test_openvpn-auth-script COMMAND test_openvpn-auth-script)
