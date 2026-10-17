cmake_minimum_required(VERSION 3.15)
project(test_libax25 C)

# Find the package via Conan-generated CMakeDeps
find_package(libax25 REQUIRED)

add_executable(test_libax25 test.c)
target_link_libraries(test_libax25 libax25::libax25)

enable_testing()
add_test(NAME test_libax25 COMMAND test_libax25)
