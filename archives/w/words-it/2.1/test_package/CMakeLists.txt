cmake_minimum_required(VERSION 3.15)
project(test_words_it LANGUAGES CXX)

add_executable(test_words_it test_words_it.cpp)
target_compile_features(test_words_it PRIVATE cxx_std_17)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    add_executable(test_words_it_ohos test_words_it_ohos.cpp)
    target_compile_features(test_words_it_ohos PRIVATE cxx_std_17)
endif()
