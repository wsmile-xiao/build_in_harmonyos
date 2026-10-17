cmake_minimum_required(VERSION 3.21)
project(test_hypre LANGUAGES C)

find_package(HYPRE CONFIG REQUIRED)

add_executable(test_hypre test.c)
target_link_libraries(test_hypre PRIVATE HYPRE::HYPRE)
