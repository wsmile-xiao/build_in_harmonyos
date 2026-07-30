cmake_minimum_required(VERSION 3.15)
project(mt32emu_consumer LANGUAGES CXX)

find_package(MT32Emu CONFIG REQUIRED)

add_executable(mt32emu_consumer test_package.cpp)
target_compile_features(mt32emu_consumer PRIVATE cxx_std_11)
target_link_libraries(mt32emu_consumer PRIVATE MT32Emu::mt32emu)
