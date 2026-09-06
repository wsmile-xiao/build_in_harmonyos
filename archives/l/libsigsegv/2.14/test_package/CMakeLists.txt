cmake_minimum_required(VERSION 3.15)
project(test_libsigsegv C)

# Find the package via Conan-generated CMakeDeps
find_package(libsigsegv REQUIRED)

add_executable(test_libsigsegv test.c)
target_link_libraries(test_libsigsegv libsigsegv::libsigsegv)

enable_testing()
add_test(NAME test_libsigsegv COMMAND test_libsigsegv)
