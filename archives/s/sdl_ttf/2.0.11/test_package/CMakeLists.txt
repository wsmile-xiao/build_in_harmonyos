cmake_minimum_required(VERSION 3.15)
project(sdl_ttf_consumer LANGUAGES C)

include(CTest)
enable_testing()

find_package(SDL CONFIG REQUIRED)
find_package(SDL_ttf CONFIG REQUIRED)
add_executable(test_sdl_ttf test.c)
target_include_directories(
    test_sdl_ttf PRIVATE "${sdl12-compat_PACKAGE_FOLDER_RELEASE}/include/SDL"
)
target_link_libraries(test_sdl_ttf PRIVATE SDL_ttf::SDL_ttf)
add_test(NAME sdl_ttf_api COMMAND test_sdl_ttf)
