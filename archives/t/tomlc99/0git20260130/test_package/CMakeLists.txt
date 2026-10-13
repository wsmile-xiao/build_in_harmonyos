cmake_minimum_required(VERSION 3.15)
project(tomlc99_smoke C)

find_package(libtoml REQUIRED CONFIG)

add_executable(tomlc99_smoke main.c)
target_link_libraries(tomlc99_smoke PRIVATE libtoml::libtoml)

if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
  add_executable(tomlc99_harmony harmony_tests/hmdfs_toml.c)
  target_link_libraries(tomlc99_harmony PRIVATE libtoml::libtoml)
endif()
