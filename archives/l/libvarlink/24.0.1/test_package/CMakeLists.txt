cmake_minimum_required(VERSION 3.15)
project(test_libvarlink C)

# Find the package via Conan-generated CMakeDeps
find_package(libvarlink REQUIRED)

add_executable(test_libvarlink test.c)
target_link_libraries(test_libvarlink libvarlink::libvarlink)

enable_testing()
add_test(NAME test_libvarlink COMMAND test_libvarlink)
