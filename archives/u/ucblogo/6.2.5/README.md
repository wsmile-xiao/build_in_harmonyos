# UCBLogo

> Berkeley Logo 解释器，支持 Logo 语言脚本和交互式命令行使用。

## 简介

UCBLogo（Berkeley Logo）是经典 Logo 教学语言的 C 实现，提供过程定义、列表、文件操作、数学、宏、对象扩展等能力。6.2.5 使用 Autotools 构建，命令行入口为 `ucblogo`。

本配方针对 OpenHarmony 终端环境关闭 wxWidgets、X11 和文档输出，保留解释器、脚本执行、文件处理和可选对象系统。

## OHOS 适配要点

- 使用官方 6.2.5 release 源码包；包内已包含完整 `configure`、`Makefile.in` 和 `config.h.in`，不依赖设备侧 Autotools 生成工具。
- 使用仓库发布的静态 `ncurses/6.4`（`shared=False`）提供 termcap API。
- OpenHarmony musl 没有 `termio.h`，补丁改用 `termios.h`。
- 不启用 wxWidgets 和 X11，因此没有 GUI 海龟窗口依赖。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| ncurses | 6.4 (shared=False) | 仓库静态终端库，提供 termcap 函数 |

## 功能验证

```bash
printf 'PRINT SUM 20 22\nBYE\n' | ucblogo -
```

预期输出包含 `42`。

## 参考

- [源码仓库](https://github.com/jrincayc/ucblogo-code)
- [6.2.5 tag](https://github.com/jrincayc/ucblogo-code/tree/version_6.2.5)
