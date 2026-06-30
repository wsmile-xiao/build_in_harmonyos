# jove

JOVE (Jonathan's Own Version of Emacs) — 轻量级 Emacs 风格文本编辑器，具有 vi 级别的内存占用。

## 软件信息

| 属性 | 值 |
|------|------|
| 名称 | jove |
| 描述 | Emacs-style editor with vi-like memory requirements |
| 主页 | https://github.com/jonmacs/jove |
| 构建系统 | Makefile (plain, 无 configure 脚本) |
| 语言 | C |
| 外部依赖 | 无（使用内置 termcap，JTC 模式） |
| 许可证 | 自由许可（无 GPL 限制） |

## 版本索引

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 4.17.5.5 | built | 2026-06-17 | 首次编译，HarmonyOS 平台适配 |

## 编译要点

- HarmonyOS 的 `uname -s` 返回 "HarmonyOS"，需设置 `SYSDEFS="-DLinux -DJTC"` 以匹配 sysdep.h 的条件编译
- `JTMPDIR` 默认 `/var/tmp` 在 HarmonyOS 上只读，需重定向到 `$TMPDIR/jove-tmp`
- 使用 JTC 模式（内置 termcap），消除对 ncurses/termcap 库的依赖
- 无 configure 脚本，直接使用 `make` + 变量编译
