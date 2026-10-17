cmake_minimum_required(VERSION 3.15)
project(ekg2_test C)

find_program(EKG2_BIN ekg2 HINTS ENV PATH)

add_executable(ekg2_test test.c)
if(EKG2_BIN)
    target_compile_definitions(ekg2_test PRIVATE
        TEST_EKG2_PATH="${EKG2_BIN}")
endif()
