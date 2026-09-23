# Pipes.sh

Animated pipes terminal screensaver — 终端管道动画屏保。

Pure Bash script that displays animated pipes on the terminal. Supports multiple pipe types, colors, and frame rates.

## Runtime Dependencies

- Bash 4+
- ncurses (tput command)

## Usage

```bash
pipes.sh              # default animation
pipes.sh -t 0         # heavy pipe characters
pipes.sh -t 1         # curved pipe characters
pipes.sh -p 5 -f 20   # 5 pipes at 20 FPS
```

Press any key to exit.
