cmake_minimum_required(VERSION 3.15)
project(test_librb C)

# Find the package via Conan-generated CMakeDeps
find_package(librb REQUIRED)

add_executable(test_librb test_librb.c)
target_link_libraries(test_librb librb::librb)

enable_testing()
add_test(NAME test_librb COMMAND test_librb)
