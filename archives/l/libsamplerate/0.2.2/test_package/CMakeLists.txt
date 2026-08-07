cmake_minimum_required(VERSION 3.15)
project(test_libsamplerate C)

# Find the package via Conan-generated CMakeDeps
find_package(libsamplerate REQUIRED)

add_executable(test_libsamplerate test.c)
target_link_libraries(test_libsamplerate libsamplerate::libsamplerate)

enable_testing()
add_test(NAME test_libsamplerate COMMAND test_libsamplerate)
