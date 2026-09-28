cmake_minimum_required(VERSION 3.15)
project(test_nxt C)

find_package(libnxt REQUIRED)

add_executable(test_nxt test_nxt.c)
target_link_libraries(test_nxt libnxt::libnxt)

enable_testing()
add_test(NAME test_nxt COMMAND test_nxt)
