cmake_minimum_required(VERSION 3.15)
project(test_liboeffis C)

find_package(liboeffis REQUIRED CONFIG)

add_executable(test_liboeffis src/test_package.c)
target_link_libraries(test_liboeffis PRIVATE liboeffis::liboeffis)

# OHOS musl 解析 DT_NEEDED 时不跟随符号链接，运行时库由 test() 摊平到
# 运行时目录并经 LD_LIBRARY_PATH 注入（见 test_package/conanfile.py）。
# 这里额外嵌入被测包的 RUNPATH 作为兜底，便于直接执行二进制定位 liboeffis.so.1。
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" OR CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    if(DEFINED liboeffis_PACKAGE_FOLDER_RELEASE)
        target_link_options(test_liboeffis PRIVATE
            "-Wl,-rpath,${liboeffis_PACKAGE_FOLDER_RELEASE}/lib"
        )
    endif()
endif()
