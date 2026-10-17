cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(gexiv2 REQUIRED CONFIG)

add_executable(test_gexiv2 test.c)
target_link_libraries(test_gexiv2 PRIVATE gexiv2::gexiv2)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR OHOS)
    # OHOS 的共享库 dlopen/dlsym 需要显式链接 libdl。
    target_link_libraries(test_gexiv2 PRIVATE ${CMAKE_DL_LIBS})
endif()
