cmake_minimum_required(VERSION 3.15)
project(test_clipmenu C)

# Find the package via Conan-generated CMakeDeps
find_package(clipmenu REQUIRED)

add_executable(test_clipmenu test.c)
target_link_libraries(test_clipmenu clipmenu::clipmenu)

enable_testing()
add_test(NAME test_clipmenu COMMAND test_clipmenu)
