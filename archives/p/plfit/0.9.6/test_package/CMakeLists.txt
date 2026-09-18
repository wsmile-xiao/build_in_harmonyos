cmake_minimum_required(VERSION 3.15)
project(plfit_consumer C)

find_package(plfit REQUIRED)

add_executable(plfit_consumer test.c)
target_link_libraries(plfit_consumer plfit::plfit)
