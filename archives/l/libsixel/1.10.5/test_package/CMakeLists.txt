cmake_minimum_required(VERSION 3.15)
project(test_libsixel C)

# Find the package via Conan-generated CMakeDeps
find_package(libsixel REQUIRED)

add_executable(test_libsixel test.c)
target_link_libraries(test_libsixel libsixel::libsixel)

enable_testing()
add_test(NAME test_libsixel COMMAND test_libsixel)
