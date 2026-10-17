cmake_minimum_required(VERSION 3.15)
project(test_sdl2_mixer C)

# Find the package via Conan-generated CMakeDeps
find_package(sdl2-mixer REQUIRED)

add_executable(test_sdl2_mixer test.c)
target_link_libraries(test_sdl2_mixer sdl2-mixer::sdl2-mixer)

enable_testing()
add_test(NAME test_sdl2_mixer COMMAND test_sdl2_mixer)
