cmake_minimum_required(VERSION 3.15)
project(qcbor_consumer C)

find_package(qcbor REQUIRED CONFIG)

add_executable(consumer consumer.c)
target_link_libraries(consumer PRIVATE qcbor::qcbor)
