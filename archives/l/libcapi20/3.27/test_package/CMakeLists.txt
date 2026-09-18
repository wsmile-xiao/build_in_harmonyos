cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(libcapi20 REQUIRED CONFIG)

# Adaptation tests: CAPI 2.0 message codec and library state accessors
add_executable(test_libcapi20 test.c)
target_link_libraries(test_libcapi20 PRIVATE libcapi20::libcapi20)

# HarmonyOS platform tests: module loading through the platform loader
add_executable(test_libcapi20_ohos test_ohos.c)
target_link_libraries(test_libcapi20_ohos PRIVATE libcapi20::libcapi20 ${CMAKE_DL_LIBS})
