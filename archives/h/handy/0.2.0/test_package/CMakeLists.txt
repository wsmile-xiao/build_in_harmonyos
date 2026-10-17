cmake_minimum_required(VERSION 3.5)
project(handy_consumer_test CXX)

set(CMAKE_CXX_STANDARD 11)

find_package(handy REQUIRED CONFIG)

add_executable(handy_consumer_test main.cc)
target_link_libraries(handy_consumer_test PRIVATE handy::handy)
