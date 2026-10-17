cmake_minimum_required(VERSION 3.15)
project(test_midifile LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(midifile REQUIRED)

add_executable(test_midifile test.cc)
target_link_libraries(test_midifile PRIVATE midifile::midifile)

enable_testing()
add_test(NAME test_midifile COMMAND test_midifile)
