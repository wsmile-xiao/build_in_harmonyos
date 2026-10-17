cmake_minimum_required(VERSION 3.15)
project(libsz_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libsz CONFIG REQUIRED)

add_executable(test_sz_roundtrip test_sz_roundtrip.c)
target_compile_options(test_sz_roundtrip PRIVATE -Wall -Wextra -Werror)
target_link_libraries(test_sz_roundtrip PRIVATE libsz::libsz)

add_executable(test_aec_roundtrip test_aec_roundtrip.c)
target_compile_options(test_aec_roundtrip PRIVATE -Wall -Wextra -Werror)
target_link_libraries(test_aec_roundtrip PRIVATE libsz::libsz)
