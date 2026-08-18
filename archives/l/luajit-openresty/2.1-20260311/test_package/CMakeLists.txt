cmake_minimum_required(VERSION 3.15)
project(test_luajit C)

find_package(luajit-openresty REQUIRED)

add_executable(test_luajit test.c)
target_link_libraries(test_luajit luajit-openresty::luajit-openresty)

enable_testing()
add_test(NAME test_luajit COMMAND test_luajit)
