cmake_minimum_required(VERSION 3.15)
project(test_package C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(Rhonabwy REQUIRED)

add_executable(test_rhonabwy test_rhonabwy.c)
target_link_libraries(test_rhonabwy PRIVATE Rhonabwy::Rhonabwy)
