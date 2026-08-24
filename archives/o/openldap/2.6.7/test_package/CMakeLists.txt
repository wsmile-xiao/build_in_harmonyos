cmake_minimum_required(VERSION 3.15)
project(test_openldap C)

# Find the package via Conan-generated CMakeDeps
find_package(openldap REQUIRED)

add_executable(test_openldap test.c)
target_link_libraries(test_openldap openldap::ldap openldap::lber)

enable_testing()
add_test(NAME test_openldap COMMAND test_openldap)
