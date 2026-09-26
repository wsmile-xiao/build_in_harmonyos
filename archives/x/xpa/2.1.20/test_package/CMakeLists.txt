cmake_minimum_required(VERSION 3.15)
project(xpa_consumer C)

find_package(xpa REQUIRED STATIC)

add_executable(xpa_consumer xpa_consumer.c)
target_link_libraries(xpa_consumer PRIVATE xpa::xpa)
