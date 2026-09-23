cmake_minimum_required(VERSION 3.15)
project(test_libdisasm LANGUAGES C)

find_package(libdisasm CONFIG REQUIRED)

add_executable(test_libdisasm test_libdisasm.c)
target_link_libraries(test_libdisasm PRIVATE libdisasm::libdisasm)
set_target_properties(test_libdisasm PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE libdisasm::libdisasm)
set_target_properties(test_consumer PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
