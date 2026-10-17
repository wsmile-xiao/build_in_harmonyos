cmake_minimum_required(VERSION 3.15)
project(test_libgc C)

# Find the package via Conan-generated CMakeDeps
find_package(libgc REQUIRED)

add_executable(test_libgc test.c)
target_link_libraries(test_libgc libgc::libgc)

enable_testing()
add_test(NAME test_libgc COMMAND test_libgc)
