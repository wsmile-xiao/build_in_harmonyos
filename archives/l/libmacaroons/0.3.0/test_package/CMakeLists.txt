cmake_minimum_required(VERSION 3.15)
project(libmacaroons_consumer C)

find_package(libmacaroons CONFIG REQUIRED)

add_executable(macaroons_consumer test_macaroons.c)
target_link_libraries(macaroons_consumer PRIVATE libmacaroons::libmacaroons)
