cmake_minimum_required(VERSION 3.15)
project(allegro44_consumer C)

find_package(allegro4.4 CONFIG REQUIRED)

add_executable(allegro_core_contract core_contract.c)
target_compile_definitions(allegro_core_contract PRIVATE ALLEGRO_NO_MAGIC_MAIN)
target_link_libraries(allegro_core_contract PRIVATE allegro4.4::allegro)
