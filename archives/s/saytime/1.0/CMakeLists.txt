cmake_minimum_required(VERSION 3.16)
project(saytime C)

# 上游 Makefile 只有一行：
#   cc -O -DSOUND_DIR=\"/users/mag/games/sounds/audio\" saytime.c -o saytime
# 那个 SOUND_DIR 是 1990 年作者的家目录，本机根本不存在。故这里把声音目录
# 指向包内的 share/saytime/sounds（由 conanfile.py 通过 SAYTIME_SOUNDS 注好的
# 编译期默认值），并保留补丁引入的环境变量覆盖能力。
#
# 编译器与 sysroot 全部来自 Conan 生成的 conan_toolchain.cmake。
add_executable(saytime saytime.c)
target_compile_options(saytime PRIVATE -w)
target_compile_options(saytime PRIVATE -O2)
set_property(TARGET saytime PROPERTY C_STANDARD 99)

# 补丁后的源码按「SAYTIME_SOUNDS 环境变量 > 编译期 SOUND_DIR」的顺序找声音目录。
# SAYTIME_SOUNDS_DIR 由 conanfile.py 传入，指向包内 share/saytime/sounds。
if(NOT DEFINED SAYTIME_SOUNDS_DIR)
    message(FATAL_ERROR "SAYTIME_SOUNDS_DIR 未定义 —— 由 conanfile.py 传入包内 sounds 路径")
endif()
target_compile_definitions(saytime PRIVATE SOUND_DIR="${SAYTIME_SOUNDS_DIR}")

set_target_properties(saytime PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
