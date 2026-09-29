cmake_minimum_required(VERSION 3.15)
project(test_seqan_consumer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(seqan REQUIRED)

add_executable(test_seqan_consumer seqan_consumer_case.cpp)
target_link_libraries(test_seqan_consumer PRIVATE seqan::seqan)
