cmake_minimum_required(VERSION 3.15)
project(libelas_consumer CXX)

enable_testing()

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(elas CONFIG REQUIRED)

add_executable(libelas_consumer test_libelas.cpp)
target_link_libraries(libelas_consumer PRIVATE elas::elas m)

add_test(NAME consumer_assertions COMMAND libelas_consumer)
