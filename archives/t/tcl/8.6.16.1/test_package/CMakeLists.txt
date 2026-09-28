cmake_minimum_required(VERSION 3.15)
project(test_package C)

# OHOS 交叉 toolchain 把 CMAKE_FIND_ROOT_PATH_MODE_PACKAGE 设为 ONLY（只在 sysroot 找包），
# 会导致找不到 conan 生成的 <pkg>-config.cmake。设为 BOTH 让 find_package 也搜 CMAKE_PREFIX_PATH
# （conan 生成器目录）。消费方在 OHOS toolchain 下用本包同理需要这条。
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE BOTH)

find_package(tcl REQUIRED CONFIG)

add_executable(test_tcl test.c)
target_link_libraries(test_tcl tcl::tcl ${CMAKE_DL_LIBS})
