cmake_minimum_required(VERSION 3.15)
project(libpog_consumer CXX)

enable_testing()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pog CONFIG REQUIRED)

add_executable(libpog_consumer test_libpog.cpp)
target_link_libraries(libpog_consumer PRIVATE pog::pog)

add_test(NAME consumer_assertions COMMAND libpog_consumer)
