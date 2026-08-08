cmake_minimum_required(VERSION 3.15)
project(test_chafa C)

find_package(chafa REQUIRED CONFIG)

add_executable(test_chafa test_chafa.c)
target_link_libraries(test_chafa PRIVATE chafa::chafa)
