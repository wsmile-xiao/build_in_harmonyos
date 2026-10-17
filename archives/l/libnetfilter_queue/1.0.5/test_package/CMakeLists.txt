cmake_minimum_required(VERSION 3.15)
project(test_libnetfilter_queue C)

find_package(libnetfilter_queue REQUIRED)

add_executable(test_libnetfilter_queue test.c)
target_link_libraries(test_libnetfilter_queue libnetfilter_queue::libnetfilter_queue)

enable_testing()
add_test(NAME test_libnetfilter_queue COMMAND test_libnetfilter_queue)
