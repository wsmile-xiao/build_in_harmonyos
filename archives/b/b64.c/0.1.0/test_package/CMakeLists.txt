cmake_minimum_required(VERSION 3.15)
project(test_b64.c C)

# Find the package via Conan-generated CMakeDeps
find_package(b64.c REQUIRED)

add_executable(test_b64.c test.c)
target_link_libraries(test_b64.c b64.c::b64.c)

enable_testing()
add_test(NAME test_b64.c COMMAND test_b64.c)
