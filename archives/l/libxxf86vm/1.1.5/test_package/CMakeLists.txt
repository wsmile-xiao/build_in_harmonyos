cmake_minimum_required(VERSION 3.15)
project(libxxf86vm_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libxxf86vm CONFIG REQUIRED)

add_executable(libxxf86vm_api_test test_xxf86vm.c)
target_compile_options(libxxf86vm_api_test PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxxf86vm_api_test PRIVATE libxxf86vm::libxxf86vm)
