cmake_minimum_required(VERSION 3.15)
project(test_sdl_gfx C)

# Package discovery comes from Conan's CMakeDeps generator
find_package(SDL_gfx REQUIRED)

add_executable(test_sdl_gfx test_sdl_gfx.c)
target_link_libraries(test_sdl_gfx SDL_gfx::SDL_gfx)

enable_testing()
add_test(NAME test_sdl_gfx COMMAND test_sdl_gfx)
