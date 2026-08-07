cmake_minimum_required(VERSION 3.15)
project(test_adamstark_audiofile CXX)

find_package(AudioFile REQUIRED CONFIG)

add_executable(test_adamstark_audiofile test_package.cpp)
target_link_libraries(test_adamstark_audiofile PRIVATE AudioFile::AudioFile)
target_compile_features(test_adamstark_audiofile PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_adamstark_audiofile COMMAND test_adamstark_audiofile)
