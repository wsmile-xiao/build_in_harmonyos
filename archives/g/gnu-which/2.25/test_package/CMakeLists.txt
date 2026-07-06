cmake_minimum_required(VERSION 3.15)
project(test_gnu-which C)

# Find the package via Conan-generated CMakeDeps
find_package(gnu-which REQUIRED)

add_executable(test_gnu-which test.c)
target_link_libraries(test_gnu-which gnu-which::gnu-which)

enable_testing()
add_test(NAME test_gnu-which COMMAND test_gnu-which)
