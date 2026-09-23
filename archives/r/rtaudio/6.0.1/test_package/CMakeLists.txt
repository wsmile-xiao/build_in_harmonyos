cmake_minimum_required(VERSION 3.15)
project(test_rtaudio LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(RtAudio REQUIRED CONFIG)

add_executable(test_rtaudio test.cpp)
target_link_libraries(test_rtaudio PRIVATE RtAudio::rtaudio)

enable_testing()
add_test(NAME rtaudio_dummy_boundary COMMAND test_rtaudio)
