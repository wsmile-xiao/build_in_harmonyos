cmake_minimum_required(VERSION 3.15)
project(trousers_consumer C)

find_package(trousers REQUIRED)

add_executable(trousers_consumer test_trousers.c)
set_property(TARGET trousers_consumer PROPERTY C_STANDARD 11)
target_link_libraries(trousers_consumer PRIVATE trousers::trousers)
