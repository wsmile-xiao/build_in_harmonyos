cmake_minimum_required(VERSION 3.15)
project(test_erhling-clibs C)

# Find the package via Conan-generated CMakeDeps
find_package(erhling-clibs REQUIRED)

add_executable(test_erhling-clibs test.c)
target_link_libraries(test_erhling-clibs erhling-clibs::erhling-clibs)

enable_testing()
add_test(NAME test_erhling-clibs COMMAND test_erhling-clibs)
