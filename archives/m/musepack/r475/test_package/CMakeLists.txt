cmake_minimum_required(VERSION 3.5)
project(musepack_test_package C)

find_package(musepack REQUIRED CONFIG)

add_executable(gen_wav gen_wav.c)
add_executable(check_mpc check_mpc.c)
target_link_libraries(check_mpc PRIVATE musepack::musepack)
