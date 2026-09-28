cmake_minimum_required(VERSION 3.15)
project(test_lightmapper LANGUAGES C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

find_package(lightmapper CONFIG REQUIRED)

add_executable(test_lightmapper test.c gl_shim.c)
target_link_libraries(test_lightmapper PRIVATE lightmapper::lightmapper)

enable_testing()
add_test(NAME test_lightmapper COMMAND test_lightmapper)