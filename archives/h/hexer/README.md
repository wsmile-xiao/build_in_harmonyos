# hexer

hexer 是一个基于终端的二进制文件编辑器（hex editor），支持十六进制/ASCII 视图编辑、正则表达式搜索、缓冲区操作等功能。基于 BSD-3-Clause 许可证发布。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 1.0.7 | built | 2026-06-17 |

## 构建信息

- **构建系统**: plain Makefile
- **编译器**: clang 15.0.4
- **依赖**: ncurses 6.4（静态链接 libncursesw.a）、musl libc
- **补丁数**: 6 个（见 1.0.7/patches/）

## 安装

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- hexer 1.0.7
```

安装后二进制位于 `~/usr/local/bin/hexer`，man page 位于 `~/usr/local/man/man1/hexer.1`。

## 使用

```bash
hexer file.bin          # 编辑二进制文件
hexer -R file.bin       # 只读模式
hexer -v file.bin       # 查看模式
hexer -V                # 显示版本
hexer -h                # 显示帮助
```
