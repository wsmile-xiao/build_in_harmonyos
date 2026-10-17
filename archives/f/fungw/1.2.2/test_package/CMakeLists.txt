cmake_minimum_required(VERSION 3.15)
project(test_fungw C)

# Find the package via Conan-generated CMakeDeps
find_package(fungw REQUIRED)

add_executable(test_fungw test.c)
target_link_libraries(test_fungw fungw::fungw)

enable_testing()
add_test(NAME test_fungw COMMAND test_fungw)
