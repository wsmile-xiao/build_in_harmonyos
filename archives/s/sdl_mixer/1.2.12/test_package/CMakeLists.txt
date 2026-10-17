cmake_minimum_required(VERSION 3.15)
project(sdl_mixer_consumer LANGUAGES C)

include(CTest)
enable_testing()

find_package(SDL CONFIG REQUIRED)
find_package(SDL_mixer CONFIG REQUIRED)
add_executable(test_sdl_mixer test.c)
target_include_directories(
    test_sdl_mixer PRIVATE "${sdl12-compat_PACKAGE_FOLDER_RELEASE}/include/SDL"
)
target_link_libraries(test_sdl_mixer PRIVATE SDL_mixer::SDL_mixer)
add_test(NAME sdl_mixer_api COMMAND test_sdl_mixer)
