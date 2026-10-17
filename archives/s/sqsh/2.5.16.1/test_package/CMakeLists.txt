cmake_minimum_required(VERSION 3.15)
project(test_sqsh C)

# Find the package via Conan-generated CMakeDeps
find_package(sqsh REQUIRED)

add_executable(test_sqsh test.c)
target_link_libraries(test_sqsh sqsh::sqsh)

enable_testing()
add_test(NAME test_sqsh COMMAND test_sqsh)
