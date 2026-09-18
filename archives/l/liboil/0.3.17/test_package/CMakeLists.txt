cmake_minimum_required(VERSION 3.15)
project(oil_consumer C)

find_package(liboil REQUIRED)

add_executable(oil_consumer oil_consumer.c)
target_link_libraries(oil_consumer PRIVATE liboil::liboil)
