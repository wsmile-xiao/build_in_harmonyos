cmake_minimum_required(VERSION 3.15)
project(test_spandsp C)

# Find the package via Conan-generated CMakeDeps
find_package(spandsp REQUIRED)

add_executable(test_spandsp test.c)
target_link_libraries(test_spandsp spandsp::spandsp)

enable_testing()
add_test(NAME test_spandsp COMMAND test_spandsp)
