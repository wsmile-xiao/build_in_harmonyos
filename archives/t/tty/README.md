# tty

> 上游项目：[tty-solitaire](https://github.com/mpereira/tty-solitaire)（平台任务名/Conan 包名：tty）

**Description**: Ncurses-based klondike solitaire game for the terminal.

**Website**: https://github.com/mpereira/tty-solitaire

**License**: MIT

## Compiled Versions

| Version | Status | Date | Notes |
|---------|--------|------|-------|
| 1.4.1 | published | 2026-09-30 | 裸 Makefile 构建，依赖 ncurses/6.5 静态库（-lncursesw + -DNCURSES_WIDECHAR） |

## Key Features

- 终端内克朗代克纸牌接龙（ncurses 宽字符渲染）
- 键盘操作：hjkl/方向键移动、空格选牌放牌、m/M/n 多选、q 退出
- 支持翻牌次数（--passes）、四色牌面（--four-color-deck）等选项

## Usage

```bash
ttysolitaire
```

- `ttysolitaire -v` — show version (1.4.1)
- `ttysolitaire -h` — usage
- `ttysolitaire -p <n>` — number of passes through the deck
- 终端尺寸需 ≥57x28；需有效的 TERM/TERMINFO 环境
