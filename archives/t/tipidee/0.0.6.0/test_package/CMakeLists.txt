cmake_minimum_required(VERSION 3.15)
project(tipidee_test LANGUAGES C)

find_package(tipidee CONFIG REQUIRED)
find_package(skalibs CONFIG REQUIRED)
add_executable(tipidee_test test.c)
target_link_libraries(tipidee_test PRIVATE tipidee::tipidee skalibs::skalibs)
