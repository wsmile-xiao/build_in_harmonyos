# newsraft

## 简介
newsraft 是一个轻量的终端 RSS/Atom 订阅阅读器，使用内嵌 termbox2 提供终端界面。

## OHOS 适配
- 上游 0.37 使用纯 POSIX makefile，无 autoconf/configure。
- termbox2 为内嵌 header-only 实现，不依赖 ncurses 或 stfl。
- 通过 Conan 注入 libcurl、expat、sqlite3 和 gumbo-parser 的 include/lib 路径，并显式传递至上游测试脚本。
- 版本检查和帮助命令支持无头冒烟验证。

## 依赖
- libcurl
- expat
- sqlite3
- gumbo-parser

## 参考
- https://codeberg.org/newsraft/newsraft
