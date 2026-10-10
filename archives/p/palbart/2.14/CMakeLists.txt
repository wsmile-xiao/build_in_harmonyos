cmake_minimum_required(VERSION 3.16)
project(palbart C)

# 上游只提供单文件 palbart.c（4353 行），没有构建脚本。
# 这里只声明「把一个源文件编成可执行文件」这一件事，编译器与 sysroot
# 全部来自 Conan 生成的 conan_toolchain.cmake（tools.build:compiler_executables
# 指向 clang-ohos.bat，system_name=OHOS，system_processor=aarch64）。
#
# 不使用 -Werror：palbart.c 是 1990 年代的 gnu89 代码，历史风格告警与
# 正确性无关，阻断它们只会让 CI 日志失真。-w 与上游 Makefile 口径一致。
add_executable(palbart palbart.c)
target_compile_options(palbart PRIVATE -w)

# 显式钉住 -O2 -std=gnu99：与配方文档记录的口径一致，且不随宿主默认值漂移。
target_compile_options(palbart PRIVATE -O2)
set_property(TARGET palbart PROPERTY C_STANDARD 99)

set_target_properties(palbart PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
