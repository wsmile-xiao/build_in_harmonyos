cmake_minimum_required(VERSION 3.5)
project(test_termcolor CXX)

# Find the package via Conan-generated CMakeDeps
find_package(termcolor REQUIRED)

add_executable(test_termcolor test.cpp)
target_link_libraries(test_termcolor termcolor::termcolor)

enable_testing()
add_test(NAME test_termcolor COMMAND test_termcolor)