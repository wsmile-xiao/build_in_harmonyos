cmake_minimum_required(VERSION 3.15)
project(tal_consumer LANGUAGES C)

# TAL_GEN_DIR holds error_table.h as rewritten by the packaged tal;
# the EXPECTED_* values are computed by conanfile.py from the generator
# input, independently of tal.
add_executable(tal_consumer tal_consumer.c)
target_include_directories(tal_consumer PRIVATE "${TAL_GEN_DIR}")
target_compile_definitions(tal_consumer PRIVATE
    EXPECTED_COUNT=${EXPECTED_COUNT}
    EXPECTED_SUM=${EXPECTED_SUM}L
    EXPECTED_BLOB=${EXPECTED_BLOB}
    EXPECTED_CONTINUATIONS=${EXPECTED_CONTINUATIONS}
    EXPECTED_MIN_COLUMN=${EXPECTED_MIN_COLUMN})
# Self-contained like the packaged tal, so the same binary runs natively on
# AArch64 and through qemu-aarch64 on x86 runners.
set_target_properties(tal_consumer PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_link_options(tal_consumer PRIVATE -static-pie)
