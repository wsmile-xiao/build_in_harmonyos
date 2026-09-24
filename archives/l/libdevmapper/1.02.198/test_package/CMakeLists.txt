cmake_minimum_required(VERSION 3.15)
project(test_libdevmapper C)

# Find the package via Conan-generated CMakeDeps
find_package(libdevmapper REQUIRED)

add_executable(test_libdevmapper test.c)
target_link_libraries(test_libdevmapper libdevmapper::libdevmapper)

enable_testing()
add_test(NAME test_libdevmapper COMMAND test_libdevmapper)
