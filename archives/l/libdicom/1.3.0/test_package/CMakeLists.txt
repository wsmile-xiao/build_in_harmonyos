cmake_minimum_required(VERSION 3.15)
project(test_libdicom C)

# Find the package via Conan-generated CMakeDeps
find_package(libdicom REQUIRED)

add_executable(test_libdicom test_libdicom.c)
target_link_libraries(test_libdicom PRIVATE libdicom::dicom)

enable_testing()
add_test(NAME test_libdicom COMMAND test_libdicom)
