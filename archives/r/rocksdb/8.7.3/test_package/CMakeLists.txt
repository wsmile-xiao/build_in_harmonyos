cmake_minimum_required(VERSION 3.15)
project(test_rocksdb CXX)

find_package(rocksdb REQUIRED)

add_executable(test_rocksdb test_rocksdb.cpp)
target_link_libraries(test_rocksdb rocksdb::rocksdb)
target_compile_features(test_rocksdb PRIVATE cxx_std_17)
