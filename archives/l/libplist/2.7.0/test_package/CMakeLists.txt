cmake_minimum_required(VERSION 3.15)
project(test_libplist C)

find_package(libplist-2.0 REQUIRED)

add_executable(test_libplist test.c)
target_link_libraries(test_libplist libplist::libplist)

if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
    add_executable(test_ohos test_ohos.c)
    target_link_libraries(test_ohos libplist::libplist)
endif()

enable_testing()
add_test(NAME test_libplist COMMAND test_libplist)
if(CMAKE_SYSTEM_NAME MATCHES "HarmonyOS|OHOS")
    add_test(NAME test_ohos COMMAND test_ohos)
endif()
