cmake_minimum_required(VERSION 3.15)
project(test_rtaudio_ohaudio LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(RtAudio REQUIRED CONFIG)

add_executable(test_rtaudio_ohos_device ohos_device_test.cpp)
target_link_libraries(test_rtaudio_ohos_device PRIVATE RtAudio::rtaudio)
