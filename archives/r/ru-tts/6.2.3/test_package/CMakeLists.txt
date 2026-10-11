cmake_minimum_required(VERSION 3.15)
project(ru_tts_test_package LANGUAGES C)

find_package(ru_tts CONFIG REQUIRED)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

add_executable(test_ru_tts test_ru_tts.c)
target_link_libraries(test_ru_tts PRIVATE ru_tts::ru_tts)
target_compile_features(test_ru_tts PRIVATE c_std_11)

if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
  add_executable(test_ru_tts_ohos test_ru_tts_ohos.c)
  target_link_libraries(test_ru_tts_ohos PRIVATE ru_tts::ru_tts)
  target_compile_features(test_ru_tts_ohos PRIVATE c_std_11)
endif()
