cmake_minimum_required(VERSION 3.15)
project(test_libstemmer C)

# Find the package via Conan-generated CMakeDeps
find_package(libstemmer REQUIRED)

add_executable(test_libstemmer test_libstemmer.c)
target_link_libraries(test_libstemmer libstemmer::libstemmer)

enable_testing()
add_test(NAME test_libstemmer COMMAND test_libstemmer)
