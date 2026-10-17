cmake_minimum_required(VERSION 3.15)
project(test_chntpw C)

add_executable(test_chntpw test.c)

enable_testing()
add_test(NAME test_chntpw COMMAND test_chntpw)
