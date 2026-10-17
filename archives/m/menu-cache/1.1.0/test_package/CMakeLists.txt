cmake_minimum_required(VERSION 3.15)
project(test_menu-cache C)

# Find the package via Conan-generated CMakeDeps
find_package(menu-cache REQUIRED)

add_executable(test_menu-cache test.c)
target_link_libraries(test_menu-cache menu-cache::menu-cache)

enable_testing()
add_test(NAME test_menu-cache COMMAND test_menu-cache)
