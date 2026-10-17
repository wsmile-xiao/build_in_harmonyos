cmake_minimum_required(VERSION 3.15)
project(tpm_tools_consumer C)

find_package(tpm-tools REQUIRED)

add_executable(tpm_tools_consumer test_tpm_tools.c)
set_property(TARGET tpm_tools_consumer PROPERTY C_STANDARD 11)
target_link_libraries(tpm_tools_consumer PRIVATE tpm-tools::tpm-tools)
