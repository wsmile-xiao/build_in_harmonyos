cmake_minimum_required(VERSION 3.15)
project(test_ncftp C)

# This is a standalone test - it uses system() to run the installed
# ncftp binary, so no external library linking is needed.
add_executable(test_ncftp test.c)

enable_testing()
add_test(NAME test_ncftp COMMAND test_ncftp)
