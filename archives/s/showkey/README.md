# showkey

> 显示终端按键的原始键序（keystroke echoer）。

## 简介

showkey 读取终端按键并以可打印形式回显其原始转义序列，是排查键盘映射、终端输入问题的轻量工具。上游为 Eric S. Raymond 维护的单文件 C 程序，仅依赖 POSIX termios 与 libc。

## 可用版本

| 版本 | 状态 | 构建系统 |
|------|------|----------|
| 1.10 | built | makefile |

## OHOS 适配要点

- 纯 Makefile 构建（无 configure/autotools/cmake），单文件 `showkey.c`，编译器取自 Conan 配置。
- 仅使用 POSIX termios/libc，源码与 OpenHarmony 完全兼容，无需补丁。
- HarmonyOS 要求二进制 ELF 签名后方可执行（签名在 release worker 完成）。

## 依赖

无外部依赖（仅 libc）。

## 参考

- [源码仓库](https://gitlab.com/esr/showkey)
