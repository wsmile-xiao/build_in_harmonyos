cmake_minimum_required(VERSION 3.15)
project(test_libplacebo5 C)

# Find the package via Conan-generated CMakeDeps
find_package(libplacebo5 REQUIRED)

add_executable(test_libplacebo5 test.c)
target_link_libraries(test_libplacebo5 libplacebo5::libplacebo5)

enable_testing()
add_test(NAME test_libplacebo5 COMMAND test_libplacebo5)
