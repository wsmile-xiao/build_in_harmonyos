cmake_minimum_required(VERSION 3.12.4)
project(alpaca_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(alpaca CONFIG REQUIRED)

add_executable(alpaca_test test.cpp)
target_link_libraries(alpaca_test PRIVATE alpaca::alpaca)
