cmake_minimum_required(VERSION 3.15)
project(test_argus C)

# Find the package via Conan-generated CMakeDeps
find_package(argus REQUIRED)

add_executable(test_argus test.c)
target_link_libraries(test_argus argus::argus)

enable_testing()
add_test(NAME test_argus COMMAND test_argus)
