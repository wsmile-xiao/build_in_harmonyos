cmake_minimum_required(VERSION 3.15)
project(test_osip C)

# Find the package via Conan-generated CMakeDeps
find_package(osip REQUIRED)

add_executable(test_osip test.c)
target_link_libraries(test_osip osip::osip)

enable_testing()
add_test(NAME test_osip COMMAND test_osip)
