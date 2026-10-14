cmake_minimum_required(VERSION 3.15.0)
project(rtaudio_ohos_device_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_BUILD_TYPE Release CACHE STRING "Match the Conan package configuration" FORCE)

find_package(RtAudio CONFIG REQUIRED
  PATHS "${CMAKE_PREFIX_PATH}"
  NO_DEFAULT_PATH
  NO_CMAKE_FIND_ROOT_PATH)

add_library(entry SHARED napi_init.cpp ohos_device_test.cpp)
target_compile_definitions(entry PRIVATE RTAUDIO_OHOS_APP_HOST=1)
target_link_libraries(entry PUBLIC RtAudio::rtaudio libace_napi.z.so)
