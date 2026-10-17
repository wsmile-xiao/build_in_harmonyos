cmake_minimum_required(VERSION 3.15)
project(leveldb_consumer LANGUAGES CXX)

find_package(leveldb CONFIG REQUIRED)

add_executable(test_leveldb test.cpp)
target_compile_features(test_leveldb PRIVATE cxx_std_11)
target_link_libraries(test_leveldb PRIVATE leveldb::leveldb)
