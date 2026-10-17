cmake_minimum_required(VERSION 3.15)
project(libxrandr_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libxrandr CONFIG REQUIRED)

add_executable(libxrandr_api_surface api_surface.c)
target_compile_options(libxrandr_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxrandr_api_surface PRIVATE libxrandr::libxrandr)

add_executable(libxrandr_alloc_contract alloc_contract.c)
target_compile_options(libxrandr_alloc_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxrandr_alloc_contract PRIVATE libxrandr::libxrandr)
