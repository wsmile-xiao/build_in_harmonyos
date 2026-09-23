cmake_minimum_required(VERSION 3.15)
project(test_libldap C)

# Find the package via Conan-generated CMakeDeps. Preflight proves only the
# aggregate target exists (log: "Target declared 'libldap::libldap'", no
# libldap::ldap/lber component targets), so link the aggregate which carries
# both libldap + liblber.
find_package(libldap REQUIRED)

add_executable(test_libldap test.c)
target_link_libraries(test_libldap libldap::libldap)

enable_testing()
add_test(NAME test_libldap COMMAND test_libldap)
