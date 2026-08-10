cmake_minimum_required(VERSION 3.15)
project(test_glproto C)

# Find the package via Conan-generated CMakeDeps
find_package(glproto REQUIRED)

add_executable(test_glproto test.c)
target_link_libraries(test_glproto PRIVATE glproto::glproto)

enable_testing()
add_test(NAME test_glproto COMMAND test_glproto)
