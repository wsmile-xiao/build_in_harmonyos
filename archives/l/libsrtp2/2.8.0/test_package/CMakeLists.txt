cmake_minimum_required(VERSION 3.15)
project(test_libsrtp2 C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name = libSRTP)
find_package(libSRTP REQUIRED)

add_executable(test_libsrtp2 test.c)
target_link_libraries(test_libsrtp2 libSRTP::srtp2)

enable_testing()
add_test(NAME test_libsrtp2 COMMAND test_libsrtp2)