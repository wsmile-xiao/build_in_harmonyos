cmake_minimum_required(VERSION 3.16)
project(pm-utils C)

# 上游是 autotools，但只构建两个独立的小程序，configure 阶段做的事仅限于
# 生成 config.h（探测 HAVE_* 宏）。这里不跑 configure，直接把源文件编成
# 两个可执行文件 —— 少一层 configure 依赖，也少一层跨编译不确定性。
# 编译器与 sysroot 全部来自 Conan 生成的 conan_toolchain.cmake。
foreach(t pm-pmu pm-reset-swap)
    add_executable(${t} src/${t}.c)
    target_compile_options(${t} PRIVATE -w)
    target_compile_options(${t} PRIVATE -O2)
    set_property(TARGET ${t} PROPERTY C_STANDARD 99)
    set_target_properties(${t} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
endforeach()
