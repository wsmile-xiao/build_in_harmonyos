cmake_minimum_required(VERSION 3.15)
project(test_libfuse C)

# Find the package via Conan-generated CMakeDeps
find_package(libfuse REQUIRED)

add_executable(test_libfuse test.c pthread_stubs.c)
target_link_libraries(test_libfuse libfuse::libfuse)
# fuse_common.h enforces _FILE_OFFSET_BITS=64 via #error
target_compile_definitions(test_libfuse PRIVATE _FILE_OFFSET_BITS=64)

enable_testing()
add_test(NAME test_libfuse COMMAND test_libfuse)
