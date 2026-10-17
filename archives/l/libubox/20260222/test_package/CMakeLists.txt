cmake_minimum_required(VERSION 3.15)
project(test_libubox C)

# Find the package via Conan-generated CMakeDeps
find_package(libubox REQUIRED)

add_executable(test_libubox test.c)
target_link_libraries(test_libubox libubox::libubox)

enable_testing()
add_test(NAME test_libubox COMMAND test_libubox)
