# mbw 2.0.1 适配笔记

## 状态
- conan-verify 通过（G0-G4 + L2/L4/L5）
- 命令行工具（Memory Bandwidth Benchmark），单文件 mbw.c，CMake 构建

## 适配要点
1. 版本号：任务平台标 "2"，但 Conan 不允许纯数字版本 → 用 2.0.1（对应上游 tag v2.0，适配修复后缀 R37）
2. 纯 C 单文件，无外部依赖（仅 libc），编译运行在 OHOS 正常
3. test_package 直接运行 mbw -n 1 1024（真实基准测试，3 种方法 MiB/s 输出）
4. 软件级 commands.json（命令行工具，R38）

## 依赖
- 无（仅 libc：stdio/stdlib/unistd/time/getopt）
