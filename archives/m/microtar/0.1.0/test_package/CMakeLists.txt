cmake_minimum_required(VERSION 3.15)
project(test_microtar C)

# Find the package via Conan-generated CMakeDeps
find_package(microtar REQUIRED)

add_executable(test_microtar test.c)
target_link_libraries(test_microtar microtar::microtar)

enable_testing()
add_test(NAME test_microtar COMMAND test_microtar)
