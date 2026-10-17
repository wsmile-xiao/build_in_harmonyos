cmake_minimum_required(VERSION 3.15)
project(test_libvterm C)

# Find the package via Conan-generated CMakeDeps
find_package(libvterm REQUIRED)

add_executable(test_libvterm test.c)
target_link_libraries(test_libvterm libvterm::libvterm)

enable_testing()
add_test(NAME test_libvterm COMMAND test_libvterm)
