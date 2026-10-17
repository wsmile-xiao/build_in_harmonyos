cmake_minimum_required(VERSION 3.15)
project(libidl_consumer C)

enable_testing()

find_package(libIDL-2.0 CONFIG REQUIRED)

add_executable(libidl_consumer test.c)
target_link_libraries(libidl_consumer PRIVATE libIDL::libIDL-2)

add_test(NAME consumer_assertions COMMAND libidl_consumer)
