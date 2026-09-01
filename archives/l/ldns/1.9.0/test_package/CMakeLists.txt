cmake_minimum_required(VERSION 3.15)
project(test_ldns C)

# Find packages via Conan-generated CMakeDeps
find_package(ldns REQUIRED)
find_package(openssl REQUIRED)

add_executable(test_ldns test.c)
target_link_libraries(test_ldns ldns::ldns openssl::openssl)

enable_testing()
add_test(NAME test_ldns COMMAND test_ldns)
