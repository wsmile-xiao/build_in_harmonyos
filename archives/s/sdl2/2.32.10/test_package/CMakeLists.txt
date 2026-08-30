cmake_minimum_required(VERSION 3.15)
project(test_sdl2_native C)

find_package(SDL2 CONFIG REQUIRED)

add_executable(test_sdl2_core test_core.c)
target_link_libraries(test_sdl2_core PRIVATE
    SDL2::SDL2
    SDL2::SDL2main
    SDL2::SDL2test
)

add_executable(test_sdl2_native_audio test_native_audio.c)
target_link_libraries(test_sdl2_native_audio PRIVATE SDL2::SDL2)

add_executable(test_sdl2_native_video test_native_video.c)
target_link_libraries(test_sdl2_native_video PRIVATE SDL2::SDL2)

add_executable(test_sdl2_native_video_invalid test_native_video_invalid.c)
target_link_libraries(test_sdl2_native_video_invalid PRIVATE SDL2::SDL2)
