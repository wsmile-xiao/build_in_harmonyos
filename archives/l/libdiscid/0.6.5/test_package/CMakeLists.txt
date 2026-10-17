cmake_minimum_required(VERSION 3.15)
project(test_package C)

# Find the package via Conan-generated CMakeDeps
find_package(libdiscid CONFIG REQUIRED)

# Consumer test: exercises the libdiscid API
add_executable(test_package test_package.c)
target_link_libraries(test_package libdiscid::libdiscid)

# Upstream tests: test_core and test_put (no hardware required)
add_executable(test_core upstream_tests/test.c upstream_tests/test_core.c)
target_link_libraries(test_core libdiscid::libdiscid)
target_include_directories(test_core PRIVATE upstream_tests)

add_executable(test_put upstream_tests/test.c upstream_tests/test_put.c)
target_link_libraries(test_put libdiscid::libdiscid)
target_include_directories(test_put PRIVATE upstream_tests)

enable_testing()
add_test(NAME test_package COMMAND test_package)
add_test(NAME test_core COMMAND test_core)
add_test(NAME test_put COMMAND test_put)
