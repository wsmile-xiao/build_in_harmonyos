cmake_minimum_required(VERSION 3.15)
project(libaiff_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libaiff CONFIG REQUIRED)

add_executable(test_libaiff_roundtrip test_libaiff_roundtrip.c)
target_compile_options(test_libaiff_roundtrip PRIVATE -Wall -Wextra)
target_link_libraries(test_libaiff_roundtrip PRIVATE libaiff::libaiff)

add_executable(test_libaiff_metadata test_libaiff_metadata.c)
target_compile_options(test_libaiff_metadata PRIVATE -Wall -Wextra)
target_link_libraries(test_libaiff_metadata PRIVATE libaiff::libaiff)
