cmake_minimum_required(VERSION 3.15)
project(libspectre_consumer C)

find_package(libspectre CONFIG REQUIRED)
enable_testing()

add_executable(libspectre_consumer test_package.c)
target_link_libraries(libspectre_consumer PRIVATE libspectre::libspectre)
add_test(NAME harmonyos_postscript_render COMMAND libspectre_consumer)
