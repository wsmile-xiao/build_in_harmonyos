cmake_minimum_required(VERSION 3.15)
project(test_microjson C)

# Find the package via Conan-generated CMakeDeps
find_package(microjson REQUIRED)

add_executable(test_microjson test.c)
target_link_libraries(test_microjson microjson::microjson)

enable_testing()
add_test(NAME test_microjson COMMAND test_microjson)
