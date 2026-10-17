cmake_minimum_required(VERSION 3.15)
project(libfs_consumer C)

find_package(libfs CONFIG REQUIRED)

add_executable(libfs_api_contract api_contract.c)
target_link_libraries(libfs_api_contract PRIVATE libfs::libfs)
