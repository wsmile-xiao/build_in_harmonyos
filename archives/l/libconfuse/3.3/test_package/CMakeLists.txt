cmake_minimum_required(VERSION 3.15)
project(test_libconfuse C)

# Find the package via Conan-generated CMakeDeps
find_package(libconfuse REQUIRED)

add_executable(test_libconfuse test.c)
target_link_libraries(test_libconfuse libconfuse::libconfuse)

enable_testing()
add_test(NAME test_libconfuse COMMAND test_libconfuse)
