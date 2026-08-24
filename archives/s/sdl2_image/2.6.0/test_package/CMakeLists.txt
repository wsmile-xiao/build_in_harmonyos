cmake_minimum_required(VERSION 3.15)
project(test_sdl2_image C)

# Find the package via Conan-generated CMakeDeps
find_package(sdl2_image REQUIRED)

add_executable(test_sdl2_image test.c)
target_link_libraries(test_sdl2_image sdl2_image::sdl2_image)

enable_testing()
add_test(NAME test_sdl2_image COMMAND test_sdl2_image)
