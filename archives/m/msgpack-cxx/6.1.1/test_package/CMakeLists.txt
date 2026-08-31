cmake_minimum_required(VERSION 3.15)
project(test_msgpack_cxx LANGUAGES CXX)

find_package(msgpack-cxx REQUIRED CONFIG)

add_executable(test_msgpack_cxx test.cpp)
target_link_libraries(test_msgpack_cxx PRIVATE msgpack-cxx::msgpack-cxx)
target_compile_features(test_msgpack_cxx PRIVATE cxx_std_11)
