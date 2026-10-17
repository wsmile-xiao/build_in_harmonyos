cmake_minimum_required(VERSION 3.15)
project(test_blockhash C)

enable_testing()

add_executable(test_blockhash test_blockhash.c)

add_test(NAME blockhash_version COMMAND test_blockhash)
