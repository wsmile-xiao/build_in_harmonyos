cmake_minimum_required(VERSION 3.15)
project(test_leptonlib C)

find_package(Leptonica CONFIG REQUIRED)
add_executable(test_leptonlib test.c)
target_link_libraries(test_leptonlib PRIVATE Leptonica::Leptonica)
