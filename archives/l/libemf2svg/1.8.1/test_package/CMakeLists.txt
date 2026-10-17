cmake_minimum_required(VERSION 3.15)
project(test_libemf2svg C)

find_package(libemf2svg REQUIRED)

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer libemf2svg::libemf2svg)

add_executable(test_upstream test_upstream.c)
target_link_libraries(test_upstream libemf2svg::libemf2svg)

enable_testing()
add_test(NAME test_consumer COMMAND test_consumer)
add_test(NAME test_upstream COMMAND test_upstream)
