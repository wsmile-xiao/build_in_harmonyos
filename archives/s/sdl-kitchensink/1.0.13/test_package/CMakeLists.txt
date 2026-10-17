cmake_minimum_required(VERSION 3.15)
project(test_sdl_kitchensink C)

# Package name contains a hyphen; CMake target name is set explicitly by the
# recipe (sdl_kitchensink::sdl_kitchensink), so find with the underscore name.
find_package(sdl_kitchensink REQUIRED)

add_executable(test_sdl_kitchensink test.c)
target_link_libraries(test_sdl_kitchensink sdl_kitchensink::sdl_kitchensink)

enable_testing()
add_test(NAME test_sdl_kitchensink COMMAND test_sdl_kitchensink)
set_tests_properties(test_sdl_kitchensink PROPERTIES
    ENVIRONMENT "SDL_VIDEODRIVER=dummy;SDL_AUDIODRIVER=dummy")