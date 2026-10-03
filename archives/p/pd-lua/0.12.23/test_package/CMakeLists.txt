cmake_minimum_required(VERSION 3.15)
project(test_pdlua C)

# The test binary drives the pd host from the puredata dependency.
add_executable(test_pdlua test_pdlua.c)
