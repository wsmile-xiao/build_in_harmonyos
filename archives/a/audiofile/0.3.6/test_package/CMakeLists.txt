cmake_minimum_required(VERSION 3.15)
project(test_audiofile CXX)

find_package(audiofile REQUIRED CONFIG)

add_executable(test_audiofile test_audiofile.cpp)
target_link_libraries(test_audiofile PRIVATE audiofile::audiofile)

enable_testing()
add_test(NAME audiofile_roundtrip COMMAND test_audiofile)
