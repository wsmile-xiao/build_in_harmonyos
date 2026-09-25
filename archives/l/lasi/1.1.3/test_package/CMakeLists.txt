cmake_minimum_required(VERSION 3.15)
project(lasi_test_package LANGUAGES CXX)

find_package(lasi CONFIG REQUIRED)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

add_executable(test_lasi test_lasi.cpp)
target_link_libraries(test_lasi PRIVATE lasi::lasi)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
  add_executable(test_lasi_ohos test_lasi_ohos.cpp)
  target_link_libraries(test_lasi_ohos PRIVATE lasi::lasi)
endif()
