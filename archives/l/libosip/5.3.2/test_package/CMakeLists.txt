cmake_minimum_required(VERSION 3.15)
project(libosip_consumer_test C)

find_package(libosip REQUIRED)

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE libosip::libosip)

include(CTest)
add_test(NAME consumer COMMAND test_consumer)
