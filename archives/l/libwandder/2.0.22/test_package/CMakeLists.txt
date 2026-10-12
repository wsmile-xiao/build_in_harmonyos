cmake_minimum_required(VERSION 3.15)
project(libwandder_test LANGUAGES C)

find_package(libwandder CONFIG REQUIRED)

add_executable(test_wandder test_wandder.c)
target_link_libraries(test_wandder PRIVATE libwandder::libwandder)
