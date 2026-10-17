cmake_minimum_required(VERSION 3.15)
project(test_brieflz C)

# Find the package via Conan-generated CMakeDeps
find_package(brieflz REQUIRED)

add_executable(test_brieflz test.c)
target_link_libraries(test_brieflz brieflz::brieflz)

enable_testing()
add_test(NAME test_brieflz COMMAND test_brieflz)
