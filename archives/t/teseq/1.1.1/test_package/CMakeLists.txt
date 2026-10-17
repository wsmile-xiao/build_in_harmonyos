cmake_minimum_required(VERSION 3.15)
project(teseq_test_package C)

# teseq publishes command-line tools only (no headers/libraries); the consumer
# assertions are shell-level and live in the conanfile's test().  CMake is kept
# as the (trivial) build-system entry point required by the archive spec.
add_custom_target(dummy SOURCES dummy.c)
