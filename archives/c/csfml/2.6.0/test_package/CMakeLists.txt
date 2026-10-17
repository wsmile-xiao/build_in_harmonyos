cmake_minimum_required(VERSION 3.15)
project(test_csfml LANGUAGES C)

find_package(CSFML CONFIG REQUIRED)

add_executable(test_csfml test.c)
target_link_libraries(test_csfml PRIVATE csfml-network csfml-system)
