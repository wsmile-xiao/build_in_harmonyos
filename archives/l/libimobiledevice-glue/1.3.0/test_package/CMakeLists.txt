cmake_minimum_required(VERSION 3.15)
project(test_libimobiledevice_glue C)

# Find the package via Conan-generated CMakeDeps
find_package(libimobiledevice-glue-1.0 REQUIRED)

add_executable(test_libimobiledevice_glue test.c)
target_link_libraries(test_libimobiledevice_glue libimobiledevice-glue::libimobiledevice-glue)

enable_testing()
add_test(NAME test_libimobiledevice_glue COMMAND test_libimobiledevice_glue)
