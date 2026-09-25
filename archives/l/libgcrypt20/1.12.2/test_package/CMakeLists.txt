cmake_minimum_required(VERSION 3.15)
project(libgcrypt20_consumer C)

find_package(libgcrypt20 CONFIG REQUIRED)

add_executable(libgcrypt20_consumer test.c)
target_link_libraries(libgcrypt20_consumer PRIVATE libgcrypt20::libgcrypt20)
if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(libgcrypt20_consumer PRIVATE -Wall -Wextra -Werror)
endif()
