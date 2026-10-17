cmake_minimum_required(VERSION 3.15)
project(test_ck C)

find_package(ck REQUIRED)

add_executable(test_ck test.c)
target_link_libraries(test_ck ck::ck)

enable_testing()
add_test(NAME test_ck COMMAND test_ck)
