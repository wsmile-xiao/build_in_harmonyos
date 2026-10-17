cmake_minimum_required(VERSION 3.15)
project(test_libblocksruntime C CXX)

find_package(BlocksRuntime REQUIRED)

enable_testing()

# Consumer 1: the upstream test (Block_copy of a stack block + __block counter).
add_executable(test_upstream test_upstream.c)
target_link_libraries(test_upstream PRIVATE BlocksRuntime::BlocksRuntime)
target_compile_options(test_upstream PRIVATE -fblocks)
add_test(NAME test_upstream COMMAND test_upstream)

# Consumer 2: independent C consumer (block classes / lifecycle / byref).
add_executable(test_blocks_c test_blocks_c.c)
target_link_libraries(test_blocks_c PRIVATE BlocksRuntime::BlocksRuntime)
target_compile_options(test_blocks_c PRIVATE -fblocks)
add_test(NAME test_blocks_c COMMAND test_blocks_c)

# Consumer 3: C++ consumer. No explicit -fblocks on purpose — the flag must
# arrive through BlocksRuntime::BlocksRuntime (cpp_info.cxxflags).
add_executable(test_blocks_cpp test_blocks_cpp.cpp)
target_link_libraries(test_blocks_cpp PRIVATE BlocksRuntime::BlocksRuntime)
add_test(NAME test_blocks_cpp COMMAND test_blocks_cpp)
