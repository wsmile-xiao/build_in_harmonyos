cmake_minimum_required(VERSION 3.15)
project(test_msgpack_cxx CXX)

find_package(msgpack-cxx REQUIRED)

add_executable(test_msgpack_cxx test.cpp)
target_link_libraries(test_msgpack_cxx msgpack-cxx::msgpack-cxx)

enable_testing()
add_test(NAME test_msgpack_cxx COMMAND test_msgpack_cxx)
