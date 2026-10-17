cmake_minimum_required(VERSION 3.15)
project(libxt_consumer C)

find_package(libxt CONFIG REQUIRED)

add_executable(libxt_allocation_contract allocation_contract.c)
target_link_libraries(libxt_allocation_contract PRIVATE libxt::libxt)

add_executable(libxt_context_contract context_contract.c)
target_link_libraries(libxt_context_contract PRIVATE libxt::libxt)
