cmake_minimum_required(VERSION 3.15)
project(test_rtmidi LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(rtmidi REQUIRED)

add_executable(test_rtmidi test.cc)
target_link_libraries(test_rtmidi PRIVATE rtmidi::rtmidi)

add_executable(rtmidi_dummy_workflow consumer_workflow.cc)
target_link_libraries(rtmidi_dummy_workflow PRIVATE rtmidi::rtmidi)

enable_testing()
add_test(NAME test_rtmidi COMMAND test_rtmidi)
add_test(NAME rtmidi_dummy_workflow COMMAND rtmidi_dummy_workflow)
