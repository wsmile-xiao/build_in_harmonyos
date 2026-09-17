cmake_minimum_required(VERSION 3.15)
project(test_libmustach_core C)

# Find the package via Conan-generated CMakeDeps.
find_package(libmustach-core REQUIRED)

add_executable(test_core test_core.c)
target_link_libraries(test_core libmustach-core::libmustach-core)

enable_testing()
add_test(NAME test_core COMMAND test_core)
