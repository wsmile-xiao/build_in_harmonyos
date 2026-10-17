cmake_minimum_required(VERSION 3.15)
project(test_libapparmor C)

# Find the package via Conan-generated CMakeDeps
find_package(libapparmor REQUIRED)

add_executable(test_libapparmor test.c)
target_link_libraries(test_libapparmor libapparmor::libapparmor)

enable_testing()
add_test(NAME test_libapparmor COMMAND test_libapparmor)
