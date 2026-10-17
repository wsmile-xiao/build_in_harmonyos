cmake_minimum_required(VERSION 3.15)
project(test_libshrinkwrap CXX)

# Package found through the Conan-generated CMakeDeps config.
# shrinkwrap 是 INTERFACE target；xz/zlib/zstd 作为 requires 由 CMakeDeps
# 级联提供 include 与链接信息。
find_package(shrinkwrap REQUIRED)

add_executable(test_libshrinkwrap test_libshrinkwrap.cpp)
target_link_libraries(test_libshrinkwrap PRIVATE shrinkwrap::shrinkwrap)
set_target_properties(test_libshrinkwrap PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_libshrinkwrap COMMAND test_libshrinkwrap)
