cmake_minimum_required(VERSION 3.15)
project(test_libogg C)

# Find the package via Conan-generated CMakeDeps
find_package(libogg REQUIRED)

add_executable(test_libogg test.c)
target_link_libraries(test_libogg libogg::libogg)

enable_testing()
add_test(NAME test_libogg COMMAND test_libogg)
