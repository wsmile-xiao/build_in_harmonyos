cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(Cwalk CONFIG REQUIRED)

add_executable(test_cwalk test_cwalk.c)
target_link_libraries(test_cwalk PRIVATE cwalk::cwalk)
target_compile_features(test_cwalk PRIVATE c_std_11)
