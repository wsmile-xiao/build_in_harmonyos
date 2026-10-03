cmake_minimum_required(VERSION 3.15)
project(libam7xxx_consumer C)

find_package(libam7xxx CONFIG REQUIRED)
add_executable(libam7xxx_consumer consumer.c)
target_link_libraries(libam7xxx_consumer PRIVATE libam7xxx::libam7xxx)
