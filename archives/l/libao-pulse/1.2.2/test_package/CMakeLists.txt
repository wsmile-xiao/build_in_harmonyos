cmake_minimum_required(VERSION 3.20)
project(libao_pulse_test_package C)

find_package(ao CONFIG REQUIRED)

add_executable(libao_pulse_consumer libao_pulse_consumer.c)
target_link_libraries(libao_pulse_consumer PRIVATE ao::ao)
target_compile_options(libao_pulse_consumer PRIVATE -Werror)