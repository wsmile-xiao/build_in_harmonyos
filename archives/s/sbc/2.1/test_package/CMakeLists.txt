cmake_minimum_required(VERSION 3.15)
project(test_sbc C)

find_package(SBC REQUIRED CONFIG)

add_executable(test_sbc test_sbc.c)
target_link_libraries(test_sbc PRIVATE SBC::SBC)

enable_testing()
add_test(NAME sbc_consumer COMMAND test_sbc)
