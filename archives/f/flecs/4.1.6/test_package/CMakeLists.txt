cmake_minimum_required(VERSION 3.15)
project(test_flecs C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(flecs REQUIRED)

add_executable(test_flecs test.c)
target_link_libraries(test_flecs flecs::flecs)

enable_testing()
add_test(NAME test_flecs COMMAND test_flecs)
