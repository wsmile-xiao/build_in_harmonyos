cmake_minimum_required(VERSION 3.15)
project(libdsme_consumer C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libdsme CONFIG REQUIRED)

add_executable(libdsme_consumer test.c)
target_link_libraries(libdsme_consumer PRIVATE libdsme::dsme)
