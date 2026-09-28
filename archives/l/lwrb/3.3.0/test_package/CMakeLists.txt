cmake_minimum_required(VERSION 3.15)
project(test_lwrb C)

# Find the package via Conan-generated CMakeDeps
find_package(lwrb REQUIRED)

add_executable(test_lwrb test.c)
target_link_libraries(test_lwrb lwrb::lwrb)

enable_testing()
add_test(NAME test_lwrb COMMAND test_lwrb)
