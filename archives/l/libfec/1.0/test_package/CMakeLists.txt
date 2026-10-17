cmake_minimum_required(VERSION 3.15)
project(test_libfec C)

# Find the package via Conan-generated CMakeDeps
find_package(libfec REQUIRED)

add_executable(test_libfec test.c)
target_link_libraries(test_libfec libfec::libfec)

enable_testing()
add_test(NAME test_libfec COMMAND test_libfec)
