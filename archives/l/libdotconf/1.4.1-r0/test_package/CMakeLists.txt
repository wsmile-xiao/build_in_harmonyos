cmake_minimum_required(VERSION 3.15)
project(test_libdotconf C)

# Find the package via Conan-generated CMakeDeps
find_package(libdotconf REQUIRED)

add_executable(test_libdotconf test.c)
target_link_libraries(test_libdotconf libdotconf::libdotconf)

enable_testing()
add_test(NAME test_libdotconf COMMAND test_libdotconf)
