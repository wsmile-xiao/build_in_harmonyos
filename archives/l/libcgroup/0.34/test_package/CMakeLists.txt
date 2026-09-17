cmake_minimum_required(VERSION 3.15)
project(libcgroup_test C)

find_package(libcgroup CONFIG REQUIRED)

add_executable(libcgroup_smoke main.c)
target_link_libraries(libcgroup_smoke PRIVATE libcgroup::libcgroup)

enable_testing()
add_test(NAME libcgroup_smoke COMMAND libcgroup_smoke)
