# mdp

[mdp](https://github.com/visit1985/mdp) — 命令行 Markdown 幻灯片演示工具。

## 版本

| 版本 | 状态 | 说明 |
| ---- | ---- | ---- |
| 1.0.18 | built | 2026-09-10 鸿蒙 PC aarch64 适配 |

## 概述

基于 ncursesw 的终端 Markdown 演示工具。纯 C，递归 Makefile 构建，
依赖 ncurses/6.6（宽字符 flavor），产出单二进制 `mdp`。

## 使用

```sh
mdp sample.md        # 演示 Markdown 幻灯片
mdp -d sample.md     # 调试模式：解析器统计输出到 stderr
```

详见 [1.0.18 适配笔记](./1.0.18/notes.md)。
