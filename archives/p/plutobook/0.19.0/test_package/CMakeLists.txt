cmake_minimum_required(VERSION 3.15)
project(test_plutobook C)

# Conan CMakeDeps 提供 plutobook::plutobook
find_package(plutobook REQUIRED)

add_executable(test_plutobook test.c)
target_link_libraries(test_plutobook PRIVATE plutobook::plutobook)

enable_testing()
add_test(NAME test_plutobook COMMAND test_plutobook)
