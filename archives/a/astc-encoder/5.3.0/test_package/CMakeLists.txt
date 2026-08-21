cmake_minimum_required(VERSION 3.15)
project(test_astcenc CXX)

find_package(astc-encoder REQUIRED)

add_executable(test_astcenc test_astcenc.cpp)
target_link_libraries(test_astcenc PRIVATE astc-encoder::astc-encoder)

enable_testing()
add_test(NAME test_astcenc COMMAND test_astcenc)
