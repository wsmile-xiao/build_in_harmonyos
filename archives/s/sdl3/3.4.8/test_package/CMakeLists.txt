cmake_minimum_required(VERSION 3.15)
project(test_sdl3 C)

# Find the package via Conan-generated CMakeDeps (official SDL3 config names,
# same target layout that downstream projects such as sdl2-compat use).
find_package(SDL3 REQUIRED)

add_executable(test_sdl3 test.c)
target_link_libraries(test_sdl3 PRIVATE SDL3::SDL3)

enable_testing()
add_test(NAME test_sdl3 COMMAND test_sdl3)
