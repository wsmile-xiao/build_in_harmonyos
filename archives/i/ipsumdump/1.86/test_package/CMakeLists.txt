cmake_minimum_required(VERSION 3.15)
project(test_ipsumdump C)

add_executable(test_ipsumdump test.c)

# The test binary generates its own pcap data at runtime (no binary files in repo).
enable_testing()
add_test(NAME test_ipsumdump COMMAND test_ipsumdump)
