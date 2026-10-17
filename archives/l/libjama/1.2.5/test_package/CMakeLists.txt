cmake_minimum_required(VERSION 3.15)
project(libjama_consumer CXX)

enable_testing()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(jama CONFIG REQUIRED)

add_executable(libjama_consumer test_jama.cpp)
target_link_libraries(libjama_consumer PRIVATE jama::jama m)

add_test(NAME consumer_assertions COMMAND libjama_consumer)
