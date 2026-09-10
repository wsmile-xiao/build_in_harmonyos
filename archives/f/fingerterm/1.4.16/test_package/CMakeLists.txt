cmake_minimum_required(VERSION 3.15)
project(test_fingerterm CXX)

# The tested package is an application: the test does not link against it.
# test_fingerterm performs the structural ELF verification of the shipped
# binary (magic, class, machine, dynamic section, symbol table).
add_executable(test_fingerterm test_fingerterm.cpp)
