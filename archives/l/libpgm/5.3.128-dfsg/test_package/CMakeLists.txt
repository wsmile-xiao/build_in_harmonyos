cmake_minimum_required(VERSION 3.15)
project(test_libpgm C)

# Find the package via Conan-generated CMakeDeps
find_package(libpgm REQUIRED)

add_executable(test_libpgm test.c)
# Public headers are installed under include/pgm-5.3/pgm/*.h by upstream's
# Makefile.am (share_includedir), which package_info() exports.
target_link_libraries(test_libpgm libpgm::libpgm)

enable_testing()
add_test(NAME test_libpgm COMMAND test_libpgm)
