cmake_minimum_required(VERSION 3.16)
project(zboy_ohos_sdl_test C)

find_package(sdl2 REQUIRED)

add_executable(zboy_ohos_sdl_test test_ohos.c)
target_link_libraries(zboy_ohos_sdl_test PRIVATE sdl2::sdl2)
set_target_properties(zboy_ohos_sdl_test PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
