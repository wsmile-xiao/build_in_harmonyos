cmake_minimum_required(VERSION 3.26)
project(blocks_runtime_tests LANGUAGES C)

find_package(BlocksRuntime CONFIG REQUIRED)

set(BLOCKS_RUNTIME_TESTS
    test_global_block
    test_captured_block
    test_escape_lifetime
    test_byref_capture
    test_nested_block
    test_retain_release
)

foreach(test_name IN LISTS BLOCKS_RUNTIME_TESTS)
    add_executable(${test_name} ${test_name}.c)
    target_compile_options(${test_name} PRIVATE -fblocks)
    target_link_libraries(${test_name} PRIVATE BlocksRuntime::BlocksRuntime)
endforeach()

add_executable(test_block_metadata test.c)
target_compile_options(test_block_metadata PRIVATE -fblocks)
target_link_libraries(test_block_metadata PRIVATE BlocksRuntime::BlocksRuntime)
