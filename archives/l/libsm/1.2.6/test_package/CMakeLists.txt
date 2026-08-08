cmake_minimum_required(VERSION 3.15)
project(libsm_consumer C)

find_package(libsm CONFIG REQUIRED)

add_executable(libsm_handler_contract handler_contract.c)
target_link_libraries(libsm_handler_contract PRIVATE libsm::libsm)

add_executable(libsm_memory_contract memory_contract.c)
target_link_libraries(libsm_memory_contract PRIVATE libsm::libsm)
