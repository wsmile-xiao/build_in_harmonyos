cmake_minimum_required(VERSION 3.15)
project(test_ctags C)

# L1 test: verifies ctags binary is installed and functional
add_executable(test_ctags test.c)

enable_testing()
add_test(NAME test_ctags COMMAND test_ctags)
