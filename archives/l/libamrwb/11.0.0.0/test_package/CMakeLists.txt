cmake_minimum_required(VERSION 3.15)
project(test_libamrwb C)

# Find the package via Conan-generated CMakeDeps
find_package(libamrwb REQUIRED)

add_executable(test_libamrwb test.c)
# libamrwb is pure C; test.c uses sin() from libm
target_link_libraries(test_libamrwb PRIVATE libamrwb::libamrwb m)

enable_testing()
add_test(NAME test_libamrwb COMMAND test_libamrwb)
