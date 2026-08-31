cmake_minimum_required(VERSION 3.15)
project(test_sdl2-ttf C)

# Find the package via Conan-generated CMakeDeps
find_package(sdl2-ttf REQUIRED)

add_executable(test_sdl2-ttf test.c)
target_link_libraries(test_sdl2-ttf sdl2-ttf::sdl2-ttf)

# HarmonyOS-specific platform-adaptation test
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos sdl2-ttf::sdl2-ttf)

enable_testing()
add_test(NAME test_sdl2-ttf COMMAND test_sdl2-ttf)
add_test(NAME test_ohos COMMAND test_ohos)