cmake_minimum_required(VERSION 3.15)
project(test_userspace_rcu C)

find_package(userspace-rcu REQUIRED)

add_executable(test_userspace_rcu test.c)
target_link_libraries(test_userspace_rcu userspace-rcu::userspace-rcu)
