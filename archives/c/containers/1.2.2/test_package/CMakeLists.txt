cmake_minimum_required(VERSION 3.15)
project(test_containers C)

# Find the package via Conan-generated CMakeDeps
find_package(containers REQUIRED)

add_executable(test_containers test.c)
target_link_libraries(test_containers containers::containers)

enable_testing()
add_test(NAME test_containers COMMAND test_containers)
