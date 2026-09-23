cmake_minimum_required(VERSION 3.15)
project(test_canfigger C)

find_package(canfigger REQUIRED CONFIG)

add_executable(test_canfigger test_canfigger.c)
target_link_libraries(test_canfigger PRIVATE canfigger::canfigger)

enable_testing()
add_test(NAME canfigger_consumer_test COMMAND test_canfigger)
