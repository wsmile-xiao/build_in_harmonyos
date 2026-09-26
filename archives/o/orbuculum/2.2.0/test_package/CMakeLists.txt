cmake_minimum_required(VERSION 3.15)
project(orbuculum_test C)

find_package(orbuculum CONFIG REQUIRED)

add_executable(orbuculum_cobs_test test_orb.c)
target_link_libraries(orbuculum_cobs_test PRIVATE orbuculum::orbuculum)

enable_testing()
add_test(NAME orbuculum_cobs_test COMMAND orbuculum_cobs_test)
