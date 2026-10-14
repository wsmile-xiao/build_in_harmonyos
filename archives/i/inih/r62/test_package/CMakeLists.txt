cmake_minimum_required(VERSION 3.15)
project(inih_installed_consumer C)

find_package(inih CONFIG REQUIRED)
add_executable(consumer consumer.c)
target_link_libraries(consumer PRIVATE inih::inih)
