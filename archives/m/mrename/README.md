# mrename

**Mass Rename —— 批量重命名工具**

## 简介

mrename 按 glob 模式匹配当前目录下的文件，为每个文件名添加「前缀 + 递增编号」，
可选择复制（`-c`）或直接改名（`-m`）。作者 Giancarlo Erra 于 2000 年发布 1.2 版后停更，
目前由 Debian QA Group 在 salsa.debian.org 维护打包。

```
mrename '*.jpg' item -c      # prof.jpg -> item1prof.jpg（保留原文件）
mrename '*.jpg' item -m      # prof.jpg -> item1prof.jpg（直接改名）
```

## 特性

- 两个 POSIX shell 脚本，无需编译
- `mrename` 负责参数解析与确认提示，`mcpmv` 负责逐文件复制/改名与编号
- 执行前会回显参数并要求输入 `yes` 确认，避免误批量改名

## 适配要点

- 上游脚本 shebang 声明 `#!/bin/sh`，实现却依赖 bash 专有语法
  （`test ==`、`$[ ]`、`echo -n`），在 POSIX shell 下报
  `[: ==: unexpected operator` 且功能失效 —— 本次适配将其彻底 POSIX 化，
  不引入 bash 运行期依赖
- 脚本安装在 `libexec/mrename/`，`bin/mrename` 为可重定位 wrapper，
  负责把 `libexec` 前置进 `PATH`（上游用 `find -exec mcpmv` 调用辅助脚本）

## 编译状态

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 1.2  | built | none | 2026-09-21 |

## 许可证

GPL-2.0-or-later（许可证声明位于上游 `README` 正文）
