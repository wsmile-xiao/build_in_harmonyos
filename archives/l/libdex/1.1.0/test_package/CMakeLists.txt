cmake_minimum_required(VERSION 3.15)
project(test_libdex C)

# Find the package via Conan-generated CMakeDeps
find_package(libdex REQUIRED)

add_executable(test_libdex test.c)
target_link_libraries(test_libdex libdex::libdex)

enable_testing()
add_test(NAME test_libdex COMMAND test_libdex)
