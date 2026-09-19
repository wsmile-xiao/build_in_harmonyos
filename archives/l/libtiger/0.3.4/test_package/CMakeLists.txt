cmake_minimum_required(VERSION 3.15)
project(test_libtiger LANGUAGES C)

find_package(tiger CONFIG REQUIRED)

add_executable(test_tiger test_tiger.c)
target_link_libraries(test_tiger PRIVATE tiger::tiger)
