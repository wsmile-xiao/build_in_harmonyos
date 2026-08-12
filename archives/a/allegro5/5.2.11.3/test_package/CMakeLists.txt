cmake_minimum_required(VERSION 3.5)
project(test_package C)

find_package(allegro5 REQUIRED CONFIG)

add_executable(test_package test_package.c)

# Link core + addons (ttf excluded: needs freetype, not available on OHOS)
target_link_libraries(test_package PRIVATE
    allegro5::allegro
    allegro5::allegro_color
    allegro5::allegro_memfile
    allegro5::allegro_primitives
    allegro5::allegro_font
    allegro5::allegro_image
)
