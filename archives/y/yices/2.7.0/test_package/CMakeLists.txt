cmake_minimum_required(VERSION 3.15)
project(test_yices C)

find_package(yices REQUIRED CONFIG)

add_executable(test_yices test_yices.c)
target_link_libraries(test_yices PRIVATE yices::yices)

enable_testing()
add_test(NAME yices_consumer COMMAND test_yices)
