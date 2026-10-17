cmake_minimum_required(VERSION 3.15)
project(test_libxklavier C)

# Find the package via Conan-generated CMakeDeps
find_package(libxklavier REQUIRED)

add_executable(test_libxklavier test.c)
target_link_libraries(test_libxklavier libxklavier::libxklavier)

enable_testing()
add_test(NAME test_libxklavier COMMAND test_libxklavier)
