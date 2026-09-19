# 配方注入的最小构建描述 — liborigin2 20110117
#
# 为什么需要它：上游只带一个 qmake 工程（liborigin2.pro），而 liborigin2 本身
# 不依赖任何 Qt 库（.pro 里 `QT -= gui core`，源码零 Qt 引用），qmake 只是它的
# 构建工具。HarmonyOS 上没有 Qt5 base / qmake，为构建一个生成器而把整套 Qt 拉进
# 构建依赖不划算，因此这里用 CMake 复刻 .pro 的构建语义。
#
# 本文件只描述「编译哪些源文件、产出什么库」，源文件清单与 liborigin2.pro 的
# SOURCES 完全一致（9 个 .cpp），不引入任何新的编译宏或逻辑，也不修改上游源码
# （源码侧的兼容性改动全部放在 patches/ 里，可与本文件分开审阅）。

cmake_minimum_required(VERSION 3.15)
project(liborigin2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# boost 只用到头文件（lexical_cast/format/date_time/tuple/variant/lambda 等），
# 链接期无任何 boost 符号 —— 见 notes.md 的三重证据。
find_package(Boost CONFIG REQUIRED)
# tree.hh 由 tree-hh 包提供（上游 20110117 tarball 缺这个头文件）。
find_package(tree-hh CONFIG REQUIRED)

set(LIBORIGIN2_SOURCES
    OriginFile.cpp
    OriginParser.cpp
    OriginDefaultParser.cpp
    Origin600Parser.cpp
    Origin610Parser.cpp
    Origin700Parser.cpp
    Origin750Parser.cpp
    Origin800Parser.cpp
    Origin810Parser.cpp)

# TARGET = origin2（与 liborigin2.pro 一致）
add_library(origin2 ${LIBORIGIN2_SOURCES})
add_library(Origin2::Origin2 ALIAS origin2)

target_link_libraries(origin2 PRIVATE Boost::headers tree-hh::tree-hh)

# 公共头文件都在源码根目录；Include-SPEC: 安装后放到 include/liborigin2/，
# 公共头之间的 #include "xxx.h" 因此仍能互相找到。
target_include_directories(origin2 PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include/liborigin2>)

# 与 Debian 打包的 ABI 一致：liborigin2.so.1.0.0，SONAME liborigin2.so.1
# （qmake 对 TEMPLATE=lib 且未设 VERSION 的工程默认取 1.0.0）
set_target_properties(origin2 PROPERTIES
    OUTPUT_NAME origin2
    VERSION 1.0.0
    SOVERSION 1)

install(TARGETS origin2
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin)

install(FILES
    OriginFile.h
    OriginObj.h
    OriginParser.h
    OriginDefaultParser.h
    Origin600Parser.h
    Origin610Parser.h
    Origin700Parser.h
    Origin750Parser.h
    Origin800Parser.h
    Origin810Parser.h
    endianfstream.hh
    DESTINATION include/liborigin2)
