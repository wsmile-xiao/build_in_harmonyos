cmake_minimum_required(VERSION 3.15)
project(test_nanosvg C)
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(NanoSVG REQUIRED)

add_executable(test_nanosvg test.c)
target_link_libraries(test_nanosvg PRIVATE NanoSVG::nanosvg NanoSVG::nanosvgrast)

enable_testing()
add_test(NAME test_nanosvg COMMAND test_nanosvg)
