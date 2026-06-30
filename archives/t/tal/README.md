# tal (Trailer Alignment)

**描述**: tal (trailer alignment) 是一个命令行过滤器，用于将多行文本末尾的共同字符（trailers）水平对齐。最初设计用于配合 vim 编辑器使用。

**主页**: http://home.pages.de/~jensen/tal/
**作者**: Thomas Jensen
**许可证**: 见 LICENSE 文件

## 版本列表

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 1.9 | built | makefile | 2026-06-17 |

## 功能

- 自动检测行尾的共同字符（如 C/C++ 注释 `//` 或 `/* */`）
- 将多行文本的 trailer 垂直对齐到同一列
- 支持 `-e` 选项手动指定 trailer 字符串
- 支持自定义填充字符、最大行宽、tab 宽度等

## 编译说明

tal 1.9 是一个单文件 C 程序（tal.c），使用 Makefile 构建，无 configure 脚本。

```bash
clang -fPIC -O2 -o tal tal.c
```

注意：原始 Makefile 的 `linux_tal` 目标使用 `gcc -ansi`，在本平台：
- 无 gcc → 直接使用 clang
- `-ansi` 导致 strdup 未声明 → 64 位指针截断 → segfault → 不使用 -ansi
