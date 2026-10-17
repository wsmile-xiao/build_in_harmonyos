cmake_minimum_required(VERSION 3.15)
project(test_libfec LANGUAGES C)

find_package(libfec CONFIG REQUIRED)

add_executable(test_rs test_rs.c)
target_link_libraries(test_rs PRIVATE libfec::libfec)
set_target_properties(test_rs PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

add_executable(test_viterbi test_viterbi.c)
target_link_libraries(test_viterbi PRIVATE libfec::libfec)
set_target_properties(test_viterbi PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

add_executable(test_dsp test_dsp.c)
target_link_libraries(test_dsp PRIVATE libfec::libfec)
set_target_properties(test_dsp PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE libfec::libfec)
set_target_properties(test_consumer PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED YES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
