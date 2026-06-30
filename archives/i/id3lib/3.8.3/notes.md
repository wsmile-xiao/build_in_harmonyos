# id3lib 3.8.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang/clang++
- 平台: aarch64-unknown-linux-ohos

## 遇到的问题和解决方案

| # | 问题 | 根因 | 解决方案 | 补丁状态 |
|---|------|------|----------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2003 版本缺少 HarmonyOS 分支，且使用 GUESS 变量而非 echo+exit | 修改 config.guess: 添加 `*:HarmonyOS:*:*` 检测分支，使用 `echo+exit 0` 模式 | 需 refresh-patch |
| 2 | config.sub 不识别 ohos 三元组 | 2003 版本缺少 ohos 支持 | 修改 config.sub: 添加 `linux-ohos*` 到 maybe_os, OS 白名单, `-ohos*` 映射 | 需 refresh-patch |
| 3 | configure 检查 iomanip.h 失败 | 现代 C++ 弃用 `<iomanip.h>`, 使用 `<iomanip>` | 从 configure.in 和 configure 中移除 iomanip.h 检查 | 需 refresh-patch |
| 4 | include/id3/id3lib_bitset 使用 `<iostream.h>` | 现代 C++ 弃用 `<iostream.h>` | 替换为 `<iostream>` | 需 refresh-patch |
| 5 | demo_info.cpp main(unsigned int argc) | C++ 标准要求 argc 为 int 类型 | 替换 `unsigned int` 为 `int` | 需 refresh-patch |
| 6 | examples/*.cpp 使用 `<strstream.h>` | 现代 C++ 弃用 `<strstream.h>` | 替换为 `<sstream>` | 需 refresh-patch |
| 7 | examples/*.cpp 使用 `<iostream.h>` | 现代 C++ 弃用 `<iostream.h>` | 替换为 `<iostream>` | 需 refresh-patch |
| 8 | config.status 无法创建临时文件 | HMDFS umask 077 导致 $TMPDIR 中无法创建子目录 | 使用可写目录; 不阻塞编译 | 不需要补丁 |

## 源码修改清单
1. `config.guess` - 添加 HarmonyOS 检测，改为 echo+exit0 模式
2. `config.sub` - 添加 ohos 三元组支持 (3处修改)
3. `configure.in` - 移除 iomanip.h 检查
4. `configure` - 移除 iomanip.h 检查 (for ac_header in string)
5. `include/id3/id3lib_bitset` - iostream.h → iostream
6. `examples/demo_info.cpp` - unsigned int argc → int argc
7. `examples/demo_convert.cpp` - unsigned int argc → int argc
8. `examples/demo_copy.cpp` - unsigned int argc → int argc
9. `examples/demo_tag.cpp` - unsigned int argc → int argc
10. 所有 examples/*.cpp - iostream.h → iostream
11. 所有 examples/*.cpp - strstream.h → sstream

## make check 结果
- 测试状态: PARTIAL
- id3info --version 返回 "id3info 3.8.3"
- id3cp --version 返回 "id3cp 3.8.3"
- id3tag --version 返回 "id3tag 3.8.3"
- id3lib 无自带测试套件
- 示例程序有 C++ 兼容性问题但已修复

## 最终状态
- 状态: published
- 库文件: libid3.a (静态库)
- 二进制工具: id3info, id3convert, id3cp, id3tag
---

**编译结束**: 2026-05-26 16:44
**最终状态**: published
