cmake_minimum_required(VERSION 3.15)
project(libxext_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libxext CONFIG REQUIRED)

add_executable(libxext_sync_value_contract sync_value_contract.c)
target_compile_options(libxext_sync_value_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxext_sync_value_contract PRIVATE libxext::libxext)

add_executable(libxext_registry_contract registry_contract.c)
target_compile_options(libxext_registry_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxext_registry_contract PRIVATE libxext::libxext)
