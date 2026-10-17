cmake_minimum_required(VERSION 3.15)
project(captagent_test C)

find_program(CAPTAGENT_BIN captagent HINTS ENV PATH)

add_executable(captagent_test test.c)
if(CAPTAGENT_BIN)
    target_compile_definitions(captagent_test PRIVATE
        TEST_CAPTAGENT_PATH="${CAPTAGENT_BIN}")
endif()
