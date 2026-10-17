cmake_minimum_required(VERSION 3.15)
project(libuninameslist_consumer_tests LANGUAGES C)

find_package(libuninameslist REQUIRED)

add_executable(consumer_tests consumer_tests.c)
target_link_libraries(consumer_tests PRIVATE libuninameslist::libuninameslist)

enable_testing()
add_test(NAME consumer_tests COMMAND consumer_tests)
