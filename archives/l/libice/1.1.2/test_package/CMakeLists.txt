cmake_minimum_required(VERSION 3.15)
project(libice_consumer C)

find_package(libice CONFIG REQUIRED)

add_executable(libice_auth_roundtrip auth_roundtrip.c)
target_link_libraries(libice_auth_roundtrip PRIVATE libice::libice)

add_executable(libice_api_contract api_contract.c)
target_link_libraries(libice_api_contract PRIVATE libice::libice)
