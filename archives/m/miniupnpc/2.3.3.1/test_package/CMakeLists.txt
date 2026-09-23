cmake_minimum_required(VERSION 3.14)
project(test_miniupnpc C)

find_package(miniupnpc REQUIRED)

add_executable(test_miniupnpc test_miniupnpc.c)
target_link_libraries(test_miniupnpc miniupnpc::miniupnpc)

enable_testing()
add_test(NAME miniupnpc_test COMMAND test_miniupnpc)
