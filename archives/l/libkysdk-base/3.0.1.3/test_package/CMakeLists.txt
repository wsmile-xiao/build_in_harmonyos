cmake_minimum_required(VERSION 3.15)
project(test_libkysdk-base C)

# Find the package via Conan-generated CMakeDeps
find_package(libkysdk-base REQUIRED)

add_executable(test_libkysdk-base test_kysdk.c)
target_link_libraries(test_libkysdk-base libkysdk-base::libkysdk-base)

enable_testing()
add_test(NAME test_libkysdk-base COMMAND test_libkysdk-base)
