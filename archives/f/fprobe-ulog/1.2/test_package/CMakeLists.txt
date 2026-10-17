cmake_minimum_required(VERSION 3.15)
project(test_fprobe_ulog C)

# Find the fprobe-ulog package (application type)
find_package(fprobe-ulog REQUIRED)

# Build the test binary
add_executable(test_fprobe_ulog test.c)
