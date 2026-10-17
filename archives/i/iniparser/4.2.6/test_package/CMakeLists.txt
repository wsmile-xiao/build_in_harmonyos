cmake_minimum_required(VERSION 3.15)
project(test_iniparser C)

find_package(iniparser CONFIG REQUIRED)

add_executable(test_iniparser test_iniparser.c)
target_link_libraries(test_iniparser PRIVATE iniparser::iniparser)
