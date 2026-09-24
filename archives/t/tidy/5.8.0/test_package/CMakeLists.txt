cmake_minimum_required(VERSION 3.10)
project(test_tidy C)

find_package(Tidy REQUIRED)

add_executable(test_tidy test_tidy.c)
target_link_libraries(test_tidy PRIVATE Tidy::Tidy)
