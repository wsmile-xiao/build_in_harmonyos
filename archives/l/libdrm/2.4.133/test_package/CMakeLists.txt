cmake_minimum_required(VERSION 3.15)
project(test_libdrm C)

# Find the package via Conan-generated CMakeDeps
find_package(libdrm REQUIRED)

add_executable(test_libdrm test.c)
target_link_libraries(test_libdrm libdrm::libdrm)

enable_testing()
add_test(NAME test_libdrm COMMAND test_libdrm)
