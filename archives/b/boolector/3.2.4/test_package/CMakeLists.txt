cmake_minimum_required(VERSION 3.15)
project(test_boolector C)

# Find the package via Conan-generated CMakeDeps
find_package(boolector REQUIRED)

add_executable(test_boolector test.c)
target_link_libraries(test_boolector boolector::boolector)

enable_testing()
add_test(NAME test_boolector COMMAND test_boolector)
