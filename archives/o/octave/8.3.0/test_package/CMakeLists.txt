cmake_minimum_required(VERSION 3.15)
project(test_octave C)

# Simple test: verify octave-cli --version works
# For Octave (a CLI tool, not a library), the L1 test verifies
# the binary is functional

# Find octave-cli in the package
find_program(OCTAVE_CLI octave-cli HINTS ${CMAKE_BINARY_DIR}/../..)

add_executable(test_octave test.c)
