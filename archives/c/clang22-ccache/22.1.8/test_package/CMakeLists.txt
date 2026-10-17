cmake_minimum_required(VERSION 3.15)
project(test_clang22-ccache C)

# Find the package via Conan-generated CMakeDeps
find_package(clang22-ccache REQUIRED)

add_executable(test_clang22-ccache test.c)
target_link_libraries(test_clang22-ccache clang22-ccache::clang22-ccache)

enable_testing()
add_test(NAME test_clang22-ccache COMMAND test_clang22-ccache)