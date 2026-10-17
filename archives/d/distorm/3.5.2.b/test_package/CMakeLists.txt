cmake_minimum_required(VERSION 3.15)
project(test_distorm C)

# Find the package via Conan-generated CMakeDeps
find_package(distorm REQUIRED)

add_executable(test_version test_version.c)
target_link_libraries(test_version distorm::distorm)

add_executable(test_decode test_decode.c)
target_link_libraries(test_decode distorm::distorm)

enable_testing()
add_test(NAME test_version COMMAND test_version)
add_test(NAME test_decode COMMAND test_decode)
