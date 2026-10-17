cmake_minimum_required(VERSION 3.15)
project(test_libsir C)

# Find the package via Conan-generated CMakeDeps
find_package(libsir REQUIRED)

add_executable(test_libsir test.c)
target_link_libraries(test_libsir libsir::libsir)

enable_testing()
add_test(NAME test_libsir COMMAND test_libsir)
