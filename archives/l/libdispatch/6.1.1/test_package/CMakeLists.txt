cmake_minimum_required(VERSION 3.15)
project(test_libdispatch C)

# Find the package via Conan-generated CMakeDeps
find_package(libdispatch REQUIRED)

add_executable(test_libdispatch test.c)
target_link_libraries(test_libdispatch libdispatch::libdispatch)
target_compile_options(test_libdispatch PRIVATE -fblocks)

enable_testing()
add_test(NAME test_libdispatch COMMAND test_libdispatch)
