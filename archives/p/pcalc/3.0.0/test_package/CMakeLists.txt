cmake_minimum_required(VERSION 3.15)
project(test_pcalc C)

find_package(pcalc REQUIRED)

add_executable(test_pcalc test_pcalc.c)
