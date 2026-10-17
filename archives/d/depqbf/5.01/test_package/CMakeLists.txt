cmake_minimum_required(VERSION 3.15)
project(test_depqbf C)

find_package(depqbf CONFIG REQUIRED)

add_executable(test_qdpll test_qdpll.c)
target_link_libraries(test_qdpll PRIVATE depqbf::qdpll)
