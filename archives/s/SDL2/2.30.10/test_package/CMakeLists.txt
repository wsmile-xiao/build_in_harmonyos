cmake_minimum_required(VERSION 3.15)
project(test_SDL2 C)

# Find the package via Conan-generated CMakeDeps
find_package(sdl2 REQUIRED)

add_executable(test_SDL2 test.c)
target_link_libraries(test_SDL2 sdl2::sdl2)

enable_testing()
add_test(NAME test_SDL2 COMMAND test_SDL2)
