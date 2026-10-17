cmake_minimum_required(VERSION 3.15)
project(lbreakout2_consumer C)

find_package(SDL CONFIG REQUIRED)
find_package(SDL_mixer CONFIG REQUIRED)
get_target_property(SDL_INCLUDE_DIRS SDL::SDL INTERFACE_INCLUDE_DIRECTORIES)
add_executable(test_sdl_runtime test_sdl_runtime.c)
target_include_directories(test_sdl_runtime PRIVATE ${SDL_INCLUDE_DIRS})
target_link_libraries(test_sdl_runtime PRIVATE SDL::SDL SDL_mixer::SDL_mixer)
