cmake_minimum_required(VERSION 3.15)
project(test_arduino_mighty_1284p C)

# Find the package via Conan-generated CMakeDeps
find_package(arduino-mighty-1284p REQUIRED)

add_executable(test_arduino_mighty_1284p test.c)
target_link_libraries(test_arduino_mighty_1284p arduino-mighty-1284p::arduino-mighty-1284p)

enable_testing()
add_test(NAME test_arduino_mighty_1284p COMMAND test_arduino_mighty_1284p)
