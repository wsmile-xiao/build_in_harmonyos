cmake_minimum_required(VERSION 3.15)
project(test_cglm C)

# Find the package via Conan-generated CMakeDeps
find_package(cglm REQUIRED)

add_executable(test_cglm test.c)
target_link_libraries(test_cglm cglm::cglm)

enable_testing()
add_test(NAME test_cglm COMMAND test_cglm)
