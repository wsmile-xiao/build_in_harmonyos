cmake_minimum_required(VERSION 3.15)
project(test_plutosvg C)
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps.
find_package(plutosvg CONFIG REQUIRED)

add_executable(test_plutosvg test.c)
target_link_libraries(test_plutosvg plutosvg::plutosvg)

enable_testing()
add_test(NAME test_plutosvg COMMAND test_plutosvg)
