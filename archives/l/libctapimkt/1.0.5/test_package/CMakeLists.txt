cmake_minimum_required(VERSION 3.15)
project(test_libctapimkt C)

# Find the package via Conan-generated CMakeDeps
find_package(libctapimkt REQUIRED)

add_executable(test_libctapimkt test.c)
target_link_libraries(test_libctapimkt libctapimkt::libctapimkt)

enable_testing()
add_test(NAME test_libctapimkt COMMAND test_libctapimkt)
