cmake_minimum_required(VERSION 3.15)
project(whereami_test LANGUAGES C)

find_package(whereami CONFIG REQUIRED)

add_library(module_probe SHARED module_probe.c)
target_link_libraries(module_probe PRIVATE whereami::whereami)
target_link_options(module_probe PRIVATE "-Wl,-Bsymbolic")

add_executable(whereami_test test_whereami.c)
target_link_libraries(whereami_test PRIVATE dl)
