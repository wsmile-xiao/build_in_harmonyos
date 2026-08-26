cmake_minimum_required(VERSION 3.15)
project(test_sdl2_ttf C)

find_package(SDL2_ttf REQUIRED)

# Test 1: TTF API lifecycle unit test (7 assertions)
add_executable(test_sdl2_ttf test.c)
target_link_libraries(test_sdl2_ttf PRIVATE SDL2_ttf::SDL2_ttf)

# Test 2: Version consistency test (5 assertions, mirrors upstream test-versioning.sh)
add_executable(test_version test_version.c)
target_link_libraries(test_version PRIVATE SDL2_ttf::SDL2_ttf)

# Test 3: OpenHarmony-specific headless test (5 assertions)
add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE SDL2_ttf::SDL2_ttf)

enable_testing()
add_test(NAME test_sdl2_ttf COMMAND test_sdl2_ttf)
add_test(NAME test_version COMMAND test_version)
add_test(NAME test_ohos COMMAND test_ohos)
