cmake_minimum_required(VERSION 3.15)
project(test_enca C)

# Find the package via Conan-generated CMakeDeps
find_package(enca REQUIRED)

add_executable(test_enca test.c)
target_link_libraries(test_enca enca::enca)

enable_testing()
add_test(NAME test_enca COMMAND test_enca)
