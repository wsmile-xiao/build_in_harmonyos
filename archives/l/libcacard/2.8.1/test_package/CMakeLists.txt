cmake_minimum_required(VERSION 3.16)
project(libcacard_consumer C)

find_package(libcacard CONFIG REQUIRED)

add_executable(libcacard_consumer test_cacard.c)
target_compile_features(libcacard_consumer PRIVATE c_std_99)
target_link_libraries(libcacard_consumer PRIVATE libcacard::cacard)
