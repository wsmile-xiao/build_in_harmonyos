cmake_minimum_required(VERSION 3.15)
project(test_libnfsidmap-ldap C)

# Find the package through the Conan-generated CMakeDeps config
find_package(libnfsidmap-ldap REQUIRED)

add_executable(test_libnfsidmap-ldap test.c)
target_link_libraries(test_libnfsidmap-ldap
                      libnfsidmap-ldap::libnfsidmap-ldap
                      ${CMAKE_DL_LIBS})
