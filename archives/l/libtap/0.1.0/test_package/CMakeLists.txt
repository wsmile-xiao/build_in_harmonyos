cmake_minimum_required(VERSION 3.15)
project(test_libtap C)

# Find the package via Conan-generated CMakeDeps
find_package(libtap REQUIRED)

add_executable(test_libtap test.c)
target_link_libraries(test_libtap libtap::libtap)

enable_testing()
add_test(NAME test_libtap COMMAND test_libtap)
