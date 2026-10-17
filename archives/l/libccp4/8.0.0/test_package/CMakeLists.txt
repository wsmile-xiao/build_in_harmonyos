cmake_minimum_required(VERSION 3.15)
project(test_libccp4 C)

# Find the package via Conan-generated CMakeDeps
find_package(libccp4 CONFIG REQUIRED)

add_executable(test_libccp4 test.c)
target_link_libraries(test_libccp4 PRIVATE libccp4::libccp4)
