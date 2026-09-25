cmake_minimum_required(VERSION 3.15)
project(test_screensaver_asteroids LANGUAGES CXX)

# Resolve through Conan CMakeDeps, same as any downstream Kodi deployment
# tooling; cmake_file_name is "kodi-addon-screensaver".
find_package(kodi-addon-screensaver CONFIG REQUIRED)

add_executable(test_screensaver_asteroids test_screensaver_asteroids.cpp)
target_compile_features(test_screensaver_asteroids PRIVATE cxx_std_17)
target_link_libraries(test_screensaver_asteroids PRIVATE ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME screensaver_asteroids_addon_entry_points
         COMMAND test_screensaver_asteroids ${ADDON_LIB_DIR}/screensaver.asteroids.so)
