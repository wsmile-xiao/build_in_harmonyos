cmake_minimum_required(VERSION 3.15)
project(libsnl_consumer CXX)

enable_testing()

find_package(libSNL CONFIG REQUIRED)

add_executable(libsnl_consumer test_libsnl.cpp)
target_link_libraries(libsnl_consumer PRIVATE libSNL::libSNL)

add_test(NAME consumer_assertions COMMAND libsnl_consumer)
