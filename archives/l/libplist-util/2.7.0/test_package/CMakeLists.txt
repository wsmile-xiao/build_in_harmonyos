cmake_minimum_required(VERSION 3.15)
project(test_libplist_util C)

add_executable(test_plistutil test.c)

if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
    add_executable(test_ohos test_ohos.c)
endif()

enable_testing()
add_test(NAME test_plistutil COMMAND test_plistutil)
if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
    add_test(NAME test_ohos COMMAND test_ohos)
endif()
