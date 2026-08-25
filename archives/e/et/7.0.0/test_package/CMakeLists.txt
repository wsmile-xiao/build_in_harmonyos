cmake_minimum_required(VERSION 3.15)
project(test_et CXX)

# et ships only executables (et, etserver, etterminal, htm, htmd).
# The test program verifies that the et executable can be launched
# and prints a version/help line. We link nothing from et because it
# is an application, not a library.
add_executable(test_et test.cpp)
enable_testing()
add_test(NAME test_et COMMAND test_et)
