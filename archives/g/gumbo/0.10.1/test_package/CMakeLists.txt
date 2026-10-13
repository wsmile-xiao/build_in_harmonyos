cmake_minimum_required(VERSION 3.15)
project(gumbo_smoke C)

find_package(gumbo REQUIRED CONFIG)

add_executable(gumbo_smoke main.c)
target_link_libraries(gumbo_smoke PRIVATE gumbo::gumbo)

if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
  add_executable(gumbo_harmony harmony_tests/hmdfs_loader.c)
  target_link_libraries(gumbo_harmony PRIVATE gumbo::gumbo dl)
endif()
