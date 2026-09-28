cmake_minimum_required(VERSION 3.15)
project(libforms_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

find_package(libforms CONFIG REQUIRED)

add_executable(libforms_api_surface api_surface.c)
target_compile_options(libforms_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libforms_api_surface PRIVATE libforms::libforms)

add_executable(libforms_abi_contract abi_contract.c)
target_compile_options(libforms_abi_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libforms_abi_contract PRIVATE libforms::libforms)
