cmake_minimum_required(VERSION 3.15)
project(test_polkit C)

find_package(polkit CONFIG REQUIRED)

add_executable(test_polkit test_polkit.c)
target_link_libraries(test_polkit PRIVATE polkit::polkit)
