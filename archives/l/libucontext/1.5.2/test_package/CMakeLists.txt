cmake_minimum_required(VERSION 3.15)
project(test_libucontext C)

# Find the package via Conan-generated CMakeDeps
find_package(libucontext REQUIRED)

add_executable(test_libucontext test.c)
target_link_libraries(test_libucontext libucontext::libucontext)

enable_testing()
add_test(NAME test_libucontext COMMAND test_libucontext)
