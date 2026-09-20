cmake_minimum_required(VERSION 3.15)
project(test_rocksdb CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(rocksdb REQUIRED)

add_executable(test_rocksdb test_rocksdb.cpp)
target_link_libraries(test_rocksdb rocksdb::rocksdb)

enable_testing()
add_test(NAME test_rocksdb COMMAND test_rocksdb)
