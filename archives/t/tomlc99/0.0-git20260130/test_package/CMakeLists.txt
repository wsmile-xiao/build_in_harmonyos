cmake_minimum_required(VERSION 3.15)
project(test_tomlc99 C)

find_package(tomlc99 REQUIRED)

enable_testing()

# Consumer-perspective API contract test (numbered CHECK output for CI L1).
add_executable(consumer_test consumer.c)
target_link_libraries(consumer_test PRIVATE tomlc99::tomlc99)
add_test(NAME consumer_test COMMAND consumer_test)

# Upstream unittest/t1.c — archived byte-identical (sha256 equals the copy
# inside the pinned master.tar.gz). conanfile build() stages it at
# ${CMAKE_BINARY_DIR}/upstream_unit/t1.c together with the packaged toml.h
# at ${CMAKE_BINARY_DIR}/toml.h, so the source's #include "../toml.h"
# resolves exactly as in the upstream unittest/ directory layout.
add_executable(unittest_t1 "${CMAKE_BINARY_DIR}/upstream_unit/t1.c")
target_link_libraries(unittest_t1 PRIVATE tomlc99::tomlc99)
# Release configurations define NDEBUG, which would compile assert() away —
# t1's 20 assertions must stay active (same intent as upstream toml_cat.c's
# "#ifdef NDEBUG / #undef NDEBUG" guard at the top of the file).
target_compile_options(unittest_t1 PRIVATE -UNDEBUG)
add_test(NAME unittest_t1 COMMAND unittest_t1)
