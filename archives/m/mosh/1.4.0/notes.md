# mosh 1.4.0 编译笔记

## 编译环境
- 平台: HarmonyOS aarch64
- 编译器: clang 15.0.4

## 依赖
- protobuf 21.12（手动编译）
- ncurses 6.4（静态库，手动编译）

## 关键问题
- HarmonyOS 缺少 getutxent() 函数
- 修改 config.h.in 禁用 HAVE_UTMPX_H
- utmp 功能被禁用，不影响核心功能

## 测试结果
- PASS: 5
- SKIP: 26
- FAIL: 0

## 最终状态
- 状态: built
- 二进制: mosh, mosh-client, mosh-server
