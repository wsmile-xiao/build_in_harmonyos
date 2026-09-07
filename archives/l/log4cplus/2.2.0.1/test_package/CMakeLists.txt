cmake_minimum_required(VERSION 3.12)
project(log4cplus_consumer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

find_package(log4cplus CONFIG REQUIRED)

add_executable(log4cplus_consumer test.cpp)
target_link_libraries(log4cplus_consumer PRIVATE log4cplus::log4cplus)
