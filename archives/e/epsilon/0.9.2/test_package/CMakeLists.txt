cmake_minimum_required(VERSION 3.15)
project(test_epsilon C)

# Find the package via Conan-generated CMakeDeps
find_package(epsilon REQUIRED)
# popt is a transitive dependency of epsilon
find_package(popt REQUIRED)

add_executable(test_epsilon test.c)
target_link_libraries(test_epsilon epsilon::epsilon popt::popt)

enable_testing()
add_test(NAME test_epsilon COMMAND test_epsilon)
