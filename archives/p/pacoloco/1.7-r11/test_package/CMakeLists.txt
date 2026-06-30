cmake_minimum_required(VERSION 3.15)
project(test_pacoloco C)

# Find the package via Conan-generated CMakeDeps
find_package(pacoloco REQUIRED)

add_executable(test_pacoloco test.c)
target_link_libraries(test_pacoloco pacoloco::pacoloco)

enable_testing()
add_test(NAME test_pacoloco COMMAND test_pacoloco)
