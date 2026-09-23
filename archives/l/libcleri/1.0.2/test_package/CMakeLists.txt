cmake_minimum_required(VERSION 3.15)
project(test_libcleri C)

# Find the package via Conan-generated CMakeDeps
find_package(libcleri REQUIRED)
find_package(pcre2 REQUIRED)

add_executable(test_libcleri test.c)
target_link_libraries(test_libcleri libcleri::libcleri pcre2::pcre2)

enable_testing()
add_test(NAME test_libcleri COMMAND test_libcleri)
