cmake_minimum_required(VERSION 3.15)
project(test_presage C)

# Find the package via Conan-generated CMakeDeps
find_package(presage REQUIRED)

add_executable(test_presage test.c)
target_link_libraries(test_presage presage::presage)

enable_testing()
add_test(NAME test_presage COMMAND test_presage)
