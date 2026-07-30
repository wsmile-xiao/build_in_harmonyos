cmake_minimum_required(VERSION 3.15)
project(libgcrypt_consumer C)

find_package(libgcrypt CONFIG REQUIRED)

add_executable(libgcrypt_consumer test.c)
target_link_libraries(libgcrypt_consumer PRIVATE libgcrypt::libgcrypt)
if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(libgcrypt_consumer PRIVATE -Wall -Wextra -Werror)
endif()
