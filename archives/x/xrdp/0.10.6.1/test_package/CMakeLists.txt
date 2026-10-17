cmake_minimum_required(VERSION 3.15)
project(test_xrdp C)

set(CMAKE_C_STANDARD 99)

# xrdp is packaged as an application (no public link target); the consumer
# test exercises the installed daemon over the wire (black box).
add_executable(test_rdp_wire test_rdp_wire.c)

enable_testing()
add_test(NAME test_rdp_wire COMMAND test_rdp_wire)
