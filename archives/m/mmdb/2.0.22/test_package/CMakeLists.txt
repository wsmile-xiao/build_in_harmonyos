cmake_minimum_required(VERSION 3.15)
project(mmdb_consumer_test CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(mmdb CONFIG REQUIRED)

add_executable(mmdb_consumer_test mmdb_consumer_test.cpp)
target_link_libraries(mmdb_consumer_test PRIVATE mmdb::mmdb)
