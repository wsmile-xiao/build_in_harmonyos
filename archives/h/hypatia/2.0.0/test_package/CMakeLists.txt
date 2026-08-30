cmake_minimum_required(VERSION 3.15)
project(test_hypatia C)

# Find the package via Conan-generated CMakeDeps
find_package(hypatia REQUIRED CONFIG)

add_executable(test_hypatia test.c)
# Header-only library, only need include directories
target_link_libraries(test_hypatia hypatia::hypatia)

enable_testing()
add_test(NAME test_hypatia COMMAND test_hypatia)
