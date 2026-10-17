cmake_minimum_required(VERSION 3.15)
project(test_libbacktrace C)

# Find the package via Conan-generated CMakeDeps
find_package(libbacktrace REQUIRED)

add_executable(test_libbacktrace test.c)
target_link_libraries(test_libbacktrace libbacktrace::libbacktrace)
# Debug info is required so backtrace_full can resolve function names
target_compile_options(test_libbacktrace PRIVATE -g -funwind-tables)

enable_testing()
add_test(NAME test_libbacktrace COMMAND test_libbacktrace)
