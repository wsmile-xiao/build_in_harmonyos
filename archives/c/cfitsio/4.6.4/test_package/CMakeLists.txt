cmake_minimum_required(VERSION 3.15)
project(test_cfitsio C)

# Find the package via Conan-generated CMakeDeps
find_package(cfitsio REQUIRED)

add_executable(test_cfitsio test.c)
target_link_libraries(test_cfitsio cfitsio::cfitsio)

enable_testing()
add_test(NAME test_cfitsio COMMAND test_cfitsio)
