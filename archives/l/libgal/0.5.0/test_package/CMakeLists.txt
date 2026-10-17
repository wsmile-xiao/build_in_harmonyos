cmake_minimum_required(VERSION 3.15)
project(test_gal C)

find_package(libgal CONFIG REQUIRED)

add_executable(test_gal test_gal.c)
target_link_libraries(test_gal PRIVATE libgal::libgal)
