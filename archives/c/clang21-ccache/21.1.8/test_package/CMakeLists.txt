cmake_minimum_required(VERSION 3.15)
project(test_clang21-ccache C)

# Find the package via Conan-generated CMakeDeps
find_package(clang21-ccache REQUIRED)

add_executable(test_clang21-ccache test.c)
target_link_libraries(test_clang21-ccache clang21-ccache::clang21-ccache)

enable_testing()
add_test(NAME test_clang21-ccache COMMAND test_clang21-ccache)