cmake_minimum_required(VERSION 3.15)
project(test_spice_protocol C)

find_package(spice-protocol REQUIRED)

add_executable(test_spice_protocol test_spice_protocol.c)
target_link_libraries(test_spice_protocol PRIVATE spice-protocol::spice-protocol)
set_target_properties(test_spice_protocol PROPERTIES C_STANDARD 99)
