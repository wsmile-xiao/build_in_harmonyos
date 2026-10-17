cmake_minimum_required(VERSION 3.15)
project(test_libcork C)

# Find the package via Conan-generated CMakeDeps
find_package(libcork REQUIRED)

add_executable(test_libcork test.c)
target_link_libraries(test_libcork libcork::libcork)

enable_testing()
add_test(NAME test_libcork COMMAND test_libcork)
