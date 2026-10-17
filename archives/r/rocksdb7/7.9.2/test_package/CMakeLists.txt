cmake_minimum_required(VERSION 3.15)
project(test_rocksdb7 CXX)

find_package(rocksdb7 REQUIRED)

add_executable(test_rocksdb7 test_rocksdb7.cpp)
target_link_libraries(test_rocksdb7 rocksdb7::rocksdb7)
target_compile_features(test_rocksdb7 PRIVATE cxx_std_17)
