cmake_minimum_required(VERSION 3.16)
project(test_qtspeech LANGUAGES CXX)

find_package(Qt6 6.11.1 REQUIRED COMPONENTS Core TextToSpeech)

add_executable(test_qtspeech test_qtspeech.cpp)
target_compile_features(test_qtspeech PRIVATE cxx_std_17)
target_link_libraries(test_qtspeech PRIVATE Qt6::Core Qt6::TextToSpeech)
