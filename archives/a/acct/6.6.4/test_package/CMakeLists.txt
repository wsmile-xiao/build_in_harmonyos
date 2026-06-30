cmake_minimum_required(VERSION 3.15)
project(test_acct C)

# Simple test - acct is a CLI tool, no library to link
add_executable(test_acct test.c)

enable_testing()
add_test(NAME test_acct COMMAND test_acct)
