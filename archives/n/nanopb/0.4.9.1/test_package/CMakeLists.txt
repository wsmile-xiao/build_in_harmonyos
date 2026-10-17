cmake_minimum_required(VERSION 3.15)
project(test_nanopb C)

find_package(nanopb REQUIRED CONFIG)

add_executable(test_nanopb test_nanopb.c)
target_link_libraries(test_nanopb PRIVATE nanopb::nanopb)

enable_testing()
add_test(NAME nanopb_wire_roundtrip COMMAND test_nanopb)
