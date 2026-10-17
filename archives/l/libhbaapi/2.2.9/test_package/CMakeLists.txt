cmake_minimum_required(VERSION 3.15)
project(libhbaapi_consumer C)

enable_testing()

find_package(HBAAPI CONFIG REQUIRED)

add_executable(libhbaapi_consumer test_hbaapi.c)
target_link_libraries(libhbaapi_consumer PRIVATE HBAAPI::HBAAPI)

add_test(NAME consumer_assertions COMMAND libhbaapi_consumer)
