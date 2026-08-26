cmake_minimum_required(VERSION 3.15)
project(test_cdogs-sdl C)

# The binary path is passed by test_package/conanfile.py via configure variables.
if(NOT DEFINED CDOGS_SDL_BIN)
    set(CDOGS_SDL_BIN "" CACHE PATH "Path to the cdogs-sdl binary")
endif()

add_executable(test_cdogs-sdl test.c)
target_compile_definitions(test_cdogs-sdl PRIVATE CDOGS_SDL_BIN="${CDOGS_SDL_BIN}")

enable_testing()
add_test(NAME test_cdogs-sdl COMMAND test_cdogs-sdl "${CDOGS_SDL_BIN}")