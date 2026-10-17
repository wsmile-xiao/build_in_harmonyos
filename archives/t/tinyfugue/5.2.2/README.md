# TinyFugue

> 可编程的终端 MUD 客户端。

## 简介

TinyFugue（命令名 `tf`）是历史悠久的终端 MUD 客户端，提供触发器、宏、别名、键盘绑定、多连接、日志、滚动回看和文本着色等功能。5.2.2 来自 `ingwarsw/tinyfugue` 的维护分支，并保留 GPL-2.0 许可证。

## OHOS 适配要点

- 上游为 Autotools，使用 `configure` 后 `make`，无自动测试目标。
- 核心终端能力保留，termcap 通过静态 ncursesw 提供。
- widechar 依赖 ICU，基础配方关闭；SSL、Lua、Python 也作为可选能力关闭。
- PCRE2 和 zlib 是 configure 的必需依赖。
- GitHub tag 归档不含 `.git`，配方将客户端版本号固定为 `5.2.2`。
- `tf` 是交互式 TUI 程序；无 TTY 的消费者测试只覆盖版本、帮助和 `/quit` 启动退出路径。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| PCRE2 | 10.45 | 正则表达式与模式匹配 |
| zlib | 1.3.1.1 | 连接数据处理所需的 inflate |
| ncurses | 6.4 (shared=False) | 仓库静态终端库，提供 termcap 与终端控制 |

## 功能验证

主线在 OHOS 上构建后应执行:

```bash
tf --version
tf --help
TFLIBDIR="$HOME/usr/local/share/tf-lib" tf -n -f -v -L"$TFLIBDIR" -c/quit
```

有可用 TTY 时再进行真实交互检查:

```bash
tf -n -f -L"$HOME/usr/local/share/tf-lib"
```

## 已知限制

- 本候选配方状态为 prepared/unverified，尚未声明真机构建或运行通过。
- 无上游自动回归测试，官方测试统计为 0/0。
- 关闭 widechar 后不提供完整 UTF-8 宽字符界面行为。

## 参考

- [源码仓库](https://github.com/ingwarsw/tinyfugue)
- [5.2.2 tag](https://github.com/ingwarsw/tinyfugue/tree/5.2.2)
- [原始项目页面](http://tinyfugue.sourceforge.net/)
