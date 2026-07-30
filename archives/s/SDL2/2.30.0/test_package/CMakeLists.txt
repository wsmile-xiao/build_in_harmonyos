cmake_minimum_required(VERSION 3.15)
project(test_sdl2 C)

# Find the package via Conan-generated CMakeDeps
find_package(SDL2 REQUIRED)

add_executable(test_sdl2 test.c)
target_link_libraries(test_sdl2 SDL2::SDL2)

enable_testing()
add_test(NAME test_sdl2 COMMAND test_sdl2)