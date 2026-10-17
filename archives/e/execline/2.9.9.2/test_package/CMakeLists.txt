cmake_minimum_required(VERSION 3.15)
project(test_execline LANGUAGES C)

# Find the package via Conan-generated CMakeDeps
find_package(execline REQUIRED)
find_package(skalibs REQUIRED)

add_executable(test_execline test.c)
target_link_libraries(test_execline PRIVATE execline::execline skalibs::skalibs)

enable_testing()
add_test(NAME test_execline COMMAND test_execline)
