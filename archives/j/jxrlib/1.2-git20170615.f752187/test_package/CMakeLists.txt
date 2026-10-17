cmake_minimum_required(VERSION 3.15)
project(consumer_roundtrip C)

find_package(jxrlib REQUIRED CONFIG)

add_executable(consumer_roundtrip consumer_roundtrip.c)
target_link_libraries(consumer_roundtrip PRIVATE jxrlib::jxrlib)

enable_testing()
add_test(NAME roundtrip COMMAND consumer_roundtrip)
