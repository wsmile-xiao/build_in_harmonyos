cmake_minimum_required(VERSION 3.15)
project(tgl_consumer C)

find_package(tgl REQUIRED)

add_executable(tgl_consumer test_tgl.c)
set_property(TARGET tgl_consumer PROPERTY C_STANDARD 11)
target_link_libraries(tgl_consumer PRIVATE tgl::tgl)
