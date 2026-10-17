cmake_minimum_required(VERSION 3.13)
project(gme_test CXX)

find_package(game-music-emu REQUIRED)

add_executable(gme_test test_package.cpp)
target_link_libraries(gme_test PRIVATE gme::gme)
