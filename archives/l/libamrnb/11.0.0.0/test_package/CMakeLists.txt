cmake_minimum_required(VERSION 3.15)
project(test_libamrnb C)

# Find the package via Conan-generated CMakeDeps
find_package(libamrnb REQUIRED)

add_executable(test_libamrnb test.c)
# libamrnb is pure C; test.c uses sin() from libm
target_link_libraries(test_libamrnb PRIVATE libamrnb::libamrnb m)

enable_testing()
add_test(NAME test_libamrnb COMMAND test_libamrnb)
