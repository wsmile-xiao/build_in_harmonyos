cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libcmph REQUIRED CONFIG)

add_executable(perfect_hash_contract perfect_hash_contract.c)
target_link_libraries(perfect_hash_contract PRIVATE libcmph::libcmph)
