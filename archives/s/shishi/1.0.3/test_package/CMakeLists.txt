cmake_minimum_required(VERSION 3.15)
project(test_shishi C)

find_package(shishi REQUIRED)

add_executable(test_shishi test_shishi.c)
target_link_libraries(test_shishi shishi::shishi)
