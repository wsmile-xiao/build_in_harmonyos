cmake_minimum_required(VERSION 3.15)
project(test_sdl_image C)

find_package(SDL_image REQUIRED CONFIG)
# SDL_image's API is built on the SDL 1.2 types, so the consumer needs the
# SDL 1.2 (sdl12-compat) headers and library as well.
find_package(SDL REQUIRED CONFIG)

add_executable(test_sdl_image test.c)
target_include_directories(test_sdl_image PRIVATE ${SDL1_INCLUDE_DIRS})
target_link_libraries(test_sdl_image PRIVATE SDL_image::SDL_image SDL::SDL)

# HarmonyOS-specific consumer test: exercise the headless OHOS runtime path.
add_executable(harmonyos_specific_test harmonyos_specific_test.c)
target_include_directories(harmonyos_specific_test PRIVATE ${SDL1_INCLUDE_DIRS})
target_link_libraries(harmonyos_specific_test PRIVATE SDL_image::SDL_image SDL::SDL)
