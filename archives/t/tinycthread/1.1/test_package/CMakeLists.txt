cmake_minimum_required(VERSION 3.15)
project(test_tinycthread C)

# Find the package via Conan-generated CMakeDeps
find_package(tinycthread REQUIRED)

add_executable(test_tinycthread test.c)
target_link_libraries(test_tinycthread tinycthread::tinycthread)

enable_testing()
add_test(NAME test_tinycthread COMMAND test_tinycthread)
