cmake_minimum_required(VERSION 3.15)
project(test_suil C)

find_package(suil-0 REQUIRED)

add_executable(test_suil test_suil.c)
target_link_libraries(test_suil PRIVATE suil-0::suil-0)
