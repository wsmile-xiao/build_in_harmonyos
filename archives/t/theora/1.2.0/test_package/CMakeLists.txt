cmake_minimum_required(VERSION 3.15)
project(theora_test_package LANGUAGES C)

find_package(Theora CONFIG REQUIRED)
find_package(Ogg CONFIG REQUIRED)

add_executable(test_theora test_theora.c)
target_link_libraries(
    test_theora
    PRIVATE
        Theora::theoradec
        Theora::theoraenc
        Theora::theora
        Ogg::ogg
)
