cmake_minimum_required(VERSION 3.15)
project(test_game_libretro LANGUAGES CXX)

# Resolve through Conan CMakeDeps, same as any downstream Kodi deployment
# tooling; cmake_file_name is "kodi-game-libretro".
find_package(kodi-game-libretro CONFIG REQUIRED)

add_executable(test_game_libretro test_game_libretro.cpp)
target_compile_features(test_game_libretro PRIVATE cxx_std_17)
target_link_libraries(test_game_libretro PRIVATE ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME game_libretro_addon_entry_points
         COMMAND test_game_libretro ${ADDON_LIB_DIR}/game.libretro.so)
