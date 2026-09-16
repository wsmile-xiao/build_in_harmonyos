# pdcurses

`PDCurses` 是 Public Domain 的 curses 文本界面实现（wmcbrine 维护线），提供
与 curses/panel 兼容的 API（`initscr`/`printw`/`getch`/窗口与面板操作等），
支持多平台后端（X11、SDL1/SDL2、Windows console 等）。

```c
#include <curses.h>
WINDOW *w = initscr();          /* SDL2 后端：SDL_VIDEODRIVER=dummy 可无显示初始化 */
printw("hello %d", 42);
refresh();
timeout(0);                     /* 非阻塞输入 */
int c = getch();                /* 无输入 -> ERR */
endwin();
```

- 上游仓库：https://github.com/wmcbrine/PDCurses
- 版本：3.9（tag `3.9`）
- 许可证：Public Domain
- 构建系统：makefile（sdl2 port，无 configure；静态库 `pdcurses.a`）
- 类型：库（SDL2 后端），依赖 sdl2/2.32.10

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.9 | built | 首次适配 HarmonyOS PC (aarch64)，SDL2 后端 |
