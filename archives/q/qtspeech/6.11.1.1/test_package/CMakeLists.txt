cmake_minimum_required(VERSION 3.16)
project(test_qtspeech CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS TextToSpeech Core Multimedia)

add_executable(test_qtspeech test_qtspeech.cpp)
target_link_libraries(test_qtspeech PRIVATE Qt6::TextToSpeech Qt6::Core)

set_property(TARGET test_qtspeech PROPERTY CXX_STANDARD 17)
set_property(TARGET test_qtspeech PROPERTY CXX_STANDARD_REQUIRED ON)
