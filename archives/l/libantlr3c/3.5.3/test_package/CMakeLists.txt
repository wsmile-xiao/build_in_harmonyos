cmake_minimum_required(VERSION 3.15)
project(libantlr3c_consumer_tests LANGUAGES C)

find_package(libantlr3c REQUIRED)

add_executable(consumer_tests consumer_tests.c)
target_link_libraries(consumer_tests PRIVATE libantlr3c::libantlr3c)

enable_testing()
add_test(NAME consumer_tests COMMAND consumer_tests)
