cmake_minimum_required(VERSION 3.15)
project(test_libproc2 C)

# Resolve the package through Conan-generated CMakeDeps
find_package(libproc2 REQUIRED)

add_executable(test_libproc2 test_libproc2.c)
target_link_libraries(test_libproc2 PRIVATE libproc2::libproc2)
