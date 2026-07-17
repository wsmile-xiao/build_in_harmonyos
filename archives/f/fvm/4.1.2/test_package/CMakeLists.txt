cmake_minimum_required(VERSION 3.15)
project(test_fvm C)

# Find the package via Conan-generated CMakeDeps
find_package(fvm REQUIRED)

add_executable(test_fvm test.c)
target_link_libraries(test_fvm fvm::fvm)

enable_testing()
add_test(NAME test_fvm COMMAND test_fvm)