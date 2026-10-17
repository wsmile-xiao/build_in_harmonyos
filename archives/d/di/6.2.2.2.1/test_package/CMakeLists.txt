cmake_minimum_required(VERSION 3.15)
project(PackageTest C)

find_package(di REQUIRED CONFIG)

add_executable(test_di_consumer test_di_consumer.c)
target_link_libraries(test_di_consumer PRIVATE di::di)
