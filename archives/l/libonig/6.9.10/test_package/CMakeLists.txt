cmake_minimum_required(VERSION 3.15)
project(test_libonig C)

find_package(onig CONFIG REQUIRED)

add_executable(test_onig test_onig.c)
target_link_libraries(test_onig PRIVATE onig::onig)

if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
    add_executable(test_ohos test_ohos.c)
    target_link_libraries(test_ohos PRIVATE onig::onig)
endif()

enable_testing()
add_test(NAME test_onig COMMAND test_onig)
if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
    add_test(NAME test_ohos COMMAND test_ohos)
endif()
