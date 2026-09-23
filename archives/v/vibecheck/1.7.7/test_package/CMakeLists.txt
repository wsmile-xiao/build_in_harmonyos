cmake_minimum_required(VERSION 3.15)
project(test_vibecheck C)

# vibecheck 1.7.7 is a pure-Go CLI; this C test reimplements its core
# pure-logic behaviour (arg parsing, key masking, keys path, provider env
# mapping, banner) mapping from the upstream Go Test* functions and asserts
# the exact same cases.  The test program is standalone and does not require
# the Go toolchain (matching the aes/0.7.4 and signal-tlsd/0.1.3 precedent).
add_executable(test_vibecheck test.c)

enable_testing()
add_test(NAME test_vibecheck COMMAND test_vibecheck)
