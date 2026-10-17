cmake_minimum_required(VERSION 3.15)
project(libgrapheme_consumer C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libgrapheme CONFIG REQUIRED)

add_executable(test_consumer test_consumer.c)
target_compile_options(test_consumer PRIVATE -Wall -Wextra)
target_link_libraries(test_consumer PRIVATE libgrapheme::libgrapheme)
