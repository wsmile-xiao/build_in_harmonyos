cmake_minimum_required(VERSION 3.15)
project(test_lp_solve LANGUAGES C)

find_package(lp_solve REQUIRED CONFIG)

add_executable(test_lp_solve test_lp_solve.c)
target_link_libraries(test_lp_solve PRIVATE lp_solve::lp_solve)
