cmake_minimum_required(VERSION 3.15)
project(test_libgm2 C)

# Find the package via Conan-generated CMakeDeps
find_package(libgm2 REQUIRED)

# Real consumer test: links the packaged runtime via libgm2::libgm2
# (m2iso/m2pim/m2cor/m2log/m2min + merged stdc++ stub) and asserts the
# C-callable Modula-2 runtime APIs (see test_libgm2.c). No shell test.
add_executable(test_libgm2 test_libgm2.c)
target_link_libraries(test_libgm2 libgm2::libgm2)

enable_testing()
add_test(NAME test_libgm2 COMMAND test_libgm2)
