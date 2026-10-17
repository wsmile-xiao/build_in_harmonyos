cmake_minimum_required(VERSION 3.15)
project(test_libftp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libftp REQUIRED)

add_executable(test_libftp test.cpp)
target_link_libraries(test_libftp libftp::libftp)

enable_testing()
add_test(NAME test_libftp COMMAND test_libftp)
