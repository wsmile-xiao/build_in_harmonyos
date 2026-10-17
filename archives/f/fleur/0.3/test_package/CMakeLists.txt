cmake_minimum_required(VERSION 3.15)
project(test_fleur C)

# Find the package via Conan-generated CMakeDeps
find_package(fleur REQUIRED)

add_executable(test_fleur test.c)
target_link_libraries(test_fleur fleur::fleur)

enable_testing()
add_test(NAME test_fleur COMMAND test_fleur)
