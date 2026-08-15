cmake_minimum_required(VERSION 3.15)
project(test_sound_touch CXX)

find_package(SoundTouch REQUIRED)

add_executable(test_sound_touch main.cpp)
target_link_libraries(test_sound_touch SoundTouch::SoundTouch)

enable_testing()
add_test(NAME test_sound_touch COMMAND test_sound_touch)
