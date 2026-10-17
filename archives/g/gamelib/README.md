# gamelib

GameLib — 面向 C++ 初学者的单头文件 2D 游戏开发库（skywind3000）。

- 官方仓库: https://github.com/skywind3000/GameLib
- 许可: MIT
- 语言: C++11，header-only

## 产品线

| 头文件 | 后端 | 平台 | 外部依赖 |
|--------|------|------|----------|
| `GameLib.h` | Win32 GDI | Windows | 无（零外部依赖） |
| `GameLib.SDL.h` | SDL2 | Windows / Linux / macOS / Web / OHOS | SDL2（必需）；SDL2_image/ttf/mixer（可选，自动探测） |

OHOS 适配使用 `GameLib.SDL.h`（SDL2 后端），已发布依赖: `sdl2/2.30.10`。

## 版本索引

| 版本 | 状态 | 日期 |
|------|------|------|
| 1.9.9 | built | 2026-09-19 |

## 使用方式

```cpp
#include "GameLib.SDL.h"

int main() {
    GameLib game;
    game.Open(640, 480, "My Game", true);
    while (!game.IsClosed()) {
        game.Clear(COLOR_BLACK);
        game.FillRect(10, 10, 20, 20, COLOR_RED);
        game.Update();
        game.WaitFrame(60);
    }
    return 0;
}
```
