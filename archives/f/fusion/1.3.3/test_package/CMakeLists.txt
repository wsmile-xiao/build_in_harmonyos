cmake_minimum_required(VERSION 3.15)
project(test_fusion C)

# Find the package via Conan-generated CMakeDeps
find_package(fusion REQUIRED)

add_executable(test_fusion test.c)
target_link_libraries(test_fusion fusion::fusion)

enable_testing()
add_test(NAME test_fusion COMMAND test_fusion)
