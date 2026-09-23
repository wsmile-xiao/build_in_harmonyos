cmake_minimum_required(VERSION 3.15)
project(test_monocypher C)

# Find the package via Conan-generated CMakeDeps
find_package(monocypher REQUIRED)

add_executable(test_monocypher test.c)
target_link_libraries(test_monocypher monocypher::monocypher)

enable_testing()
add_test(NAME test_monocypher COMMAND test_monocypher)
