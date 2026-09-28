cmake_minimum_required(VERSION 3.15)
project(test_krb5-sync C)

# Find the package via Conan-generated CMakeDeps
find_package(krb5-sync REQUIRED)

add_executable(test_krb5-sync test.c)
target_link_libraries(test_krb5-sync krb5-sync::krb5-sync)

enable_testing()
add_test(NAME test_krb5-sync COMMAND test_krb5-sync)
