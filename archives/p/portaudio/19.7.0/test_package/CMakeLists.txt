cmake_minimum_required(VERSION 3.15)
project(test_portaudio LANGUAGES C)

find_package(PortAudio CONFIG REQUIRED)

add_executable(test_portaudio test_portaudio.c)
target_link_libraries(test_portaudio PRIVATE PortAudio::PortAudio)
