cmake_minimum_required(VERSION 3.15)
project(test_cmocka C)

find_package(cmocka REQUIRED)

add_executable(test_cmocka test_cmocka.c)
target_link_libraries(test_cmocka PRIVATE cmocka::cmocka)
