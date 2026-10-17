cmake_minimum_required(VERSION 3.15)
project(sdl_image_consumer LANGUAGES C)

include(CTest)
enable_testing()

find_package(SDL CONFIG REQUIRED)
find_package(SDL_image CONFIG REQUIRED)
add_executable(test_sdl_image test.c)
target_include_directories(
    test_sdl_image PRIVATE "${sdl12-compat_PACKAGE_FOLDER_RELEASE}/include/SDL"
)
target_link_libraries(test_sdl_image PRIVATE SDL_image::SDL_image)
add_test(NAME sdl_image_api COMMAND test_sdl_image)
