cmake_minimum_required(VERSION 3.15)
project(test_canlock C)

find_package(canlock REQUIRED CONFIG)

add_executable(test_canlock test_canlock.c)
target_link_libraries(test_canlock PRIVATE canlock::canlock canlock::canlock-hp)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR
   CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    add_executable(test_canlock_ohos test_canlock_ohos.c)
    target_link_libraries(test_canlock_ohos PRIVATE canlock::canlock)
endif()
