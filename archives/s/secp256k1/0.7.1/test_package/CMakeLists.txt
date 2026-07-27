cmake_minimum_required(VERSION 3.15)
project(test_secp256k1 LANGUAGES C)

find_package(secp256k1 REQUIRED CONFIG)

add_executable(test_secp256k1 test.c)
target_link_libraries(test_secp256k1 PRIVATE secp256k1::secp256k1)