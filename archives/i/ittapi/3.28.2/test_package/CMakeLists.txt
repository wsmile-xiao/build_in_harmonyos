cmake_minimum_required(VERSION 3.15)
project(test_ittapi C)

find_package(ittapi REQUIRED CONFIG)

add_executable(test_ittapi_consumer test_ittapi.c)
target_link_libraries(test_ittapi_consumer PRIVATE ittapi::ittapi)
