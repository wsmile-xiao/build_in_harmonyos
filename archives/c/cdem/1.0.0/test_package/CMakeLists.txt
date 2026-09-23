cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(cdem CONFIG REQUIRED)

add_executable(test_cdem test_cdem.c)
target_link_libraries(test_cdem PRIVATE cdem::cdem)
target_compile_features(test_cdem PRIVATE c_std_11)
