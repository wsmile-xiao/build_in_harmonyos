cmake_minimum_required(VERSION 3.15)
project(libnop_consumer CXX)

enable_testing()

find_package(libnop CONFIG REQUIRED)

add_executable(libnop_consumer test_libnop.cpp)
target_link_libraries(libnop_consumer PRIVATE libnop::libnop)
set_target_properties(libnop_consumer PROPERTIES CXX_STANDARD 14 CXX_STANDARD_REQUIRED ON)

add_test(NAME consumer_assertions COMMAND libnop_consumer)
