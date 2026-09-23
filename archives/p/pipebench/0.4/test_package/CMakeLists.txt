cmake_minimum_required(VERSION 3.15)
project(pipebench_test C)

find_package(pipebench CONFIG QUIET)

add_executable(test_pipebench test_pipebench.c)

if(TARGET pipebench::pipebench)
  target_link_libraries(test_pipebench PRIVATE pipebench::pipebench)
endif()
