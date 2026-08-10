cmake_minimum_required(VERSION 3.15)
project(test_lastpass_cli C)

# Reference the tested package target
find_package(lastpass-cli REQUIRED)

add_executable(test_lastpass_cli test.c)

enable_testing()
add_test(NAME test_lastpass_cli COMMAND test_lastpass_cli)
