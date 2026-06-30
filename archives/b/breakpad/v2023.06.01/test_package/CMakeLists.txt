cmake_minimum_required(VERSION 3.15)
project(test_breakpad C)

# Find the package via Conan-generated CMakeDeps
find_package(breakpad REQUIRED)

add_executable(test_breakpad test.c)
target_link_libraries(test_breakpad breakpad::breakpad)

enable_testing()
add_test(NAME test_breakpad COMMAND test_breakpad)
