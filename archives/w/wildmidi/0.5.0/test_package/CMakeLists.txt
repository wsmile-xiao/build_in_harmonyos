cmake_minimum_required(VERSION 3.15)
project(test_wildmidi C)

find_package(WildMidi REQUIRED)

add_executable(test_wildmidi test_wildmidi.c)
# WildMidi::libwildmidi (shared) or WildMidi::libwildmidi-static (static)
if(TARGET WildMidi::libwildmidi)
    target_link_libraries(test_wildmidi WildMidi::libwildmidi)
else()
    target_link_libraries(test_wildmidi WildMidi::libwildmidi-static)
endif()

enable_testing()
add_test(NAME test_wildmidi COMMAND test_wildmidi)
