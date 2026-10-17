cmake_minimum_required(VERSION 3.15)
project(test_krb5 C)

# Find the package via Conan-generated CMakeDeps
find_package(krb5 REQUIRED)

add_executable(test_krb5 test.c)
target_link_libraries(test_krb5 krb5::krb5)

enable_testing()
add_test(NAME test_krb5 COMMAND test_krb5)
