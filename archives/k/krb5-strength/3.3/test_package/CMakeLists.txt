cmake_minimum_required(VERSION 3.15)
project(test_krb5-strength C)

# Validate that the package exposes a CMake config via CMakeDeps. The pwqual
# plugin is dlopen'ed (no link interface), so nothing is linked here; the
# functional check happens in the conanfile test() method.
find_package(krb5-strength REQUIRED)

add_executable(test_krb5-strength test.c)
# dlopen/dlsym live in libc on both glibc >= 2.34 and OHOS musl, so no
# explicit -ldl is needed.

enable_testing()
add_test(NAME test_krb5-strength COMMAND test_krb5-strength)
