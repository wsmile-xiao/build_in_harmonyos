cmake_minimum_required(VERSION 3.15)
project(test_lpsolve LANGUAGES C)

find_package(lpsolve REQUIRED CONFIG)

add_executable(test_lpsolve test_lpsolve.c)
target_link_libraries(test_lpsolve PRIVATE lpsolve::lpsolve)
