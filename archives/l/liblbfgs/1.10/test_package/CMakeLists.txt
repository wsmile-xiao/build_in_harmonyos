cmake_minimum_required(VERSION 3.15)
project(liblbfgs_test C)

find_package(LBFGS REQUIRED)

add_executable(liblbfgs_smoke main.c)
target_link_libraries(liblbfgs_smoke PRIVATE LBFGS::lib)
