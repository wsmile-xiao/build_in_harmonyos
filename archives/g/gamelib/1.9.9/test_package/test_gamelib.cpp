// gamelib 1.9.9 — 消费者测试 (L1)
// 以第三方使用者视角：仅通过 gamelib 安装后的公开头文件 GameLib.SDL.h
// 与公开 API 使用该库，验证编译、链接、调用与运行（R34）。
// 核心验证点：
//   1) GameLib.SDL.h 可被下游 C++11 程序包含并链接 SDL2
//   2) 公开静态 API（RectOverlap/CircleOverlap/PointInRect/Distance/Random）
//      返回可观察且符合预期的结果
//   3) 颜色宏 COLOR_RGB/COLOR_ARGB 与版本宏正确
#include <cassert>
#include <cstdio>
#include <cstring>

#include "GameLib.SDL.h"

int main() {
    // ---- 版本宏 ----
    assert(GAMELIB_SDL_VERSION_MAJOR == 1);
    assert(GAMELIB_SDL_VERSION_MINOR == 9);
    assert(GAMELIB_SDL_VERSION_PATCH == 9);

    // ---- 颜色宏（ARGB 格式）----
    assert(COLOR_BLACK == 0xFF000000u);
    assert(COLOR_WHITE == 0xFFFFFFFFu);
    assert(COLOR_RGB(255, 0, 0) == 0xFFFF0000u);
    assert(COLOR_RGB(0, 255, 0) == 0xFF00FF00u);
    assert(COLOR_ARGB(128, 10, 20, 30) == 0x800A141Eu);

    // ---- 碰撞检测静态 API（真实调用 + 可观察结果断言）----
    // 矩形重叠：两个相交矩形
    assert(GameLib::RectOverlap(0, 0, 10, 10, 5, 5, 10, 10) == true);
    // 矩形不重叠：一个在另一个右上方
    assert(GameLib::RectOverlap(0, 0, 5, 5, 10, 10, 5, 5) == false);
    // 边贴边不算重叠
    assert(GameLib::RectOverlap(0, 0, 10, 10, 10, 0, 10, 10) == false);

    // 圆重叠：圆心距 < 半径和
    assert(GameLib::CircleOverlap(0, 0, 5, 4, 0, 5) == true);
    // 圆不重叠：圆心距 > 半径和
    assert(GameLib::CircleOverlap(0, 0, 1, 10, 0, 1) == false);

    // 点在矩形内/外
    assert(GameLib::PointInRect(5, 5, 0, 0, 10, 10) == true);
    assert(GameLib::PointInRect(10, 10, 0, 0, 10, 10) == false);

    // 两点距离（3-4-5 直角三角形）
    float d = GameLib::Distance(0, 0, 3, 4);
    assert(d > 4.99f && d < 5.01f);

    // 随机数范围
    for (int i = 0; i < 100; i++) {
        int r = GameLib::Random(3, 7);
        assert(r >= 3 && r <= 7);
    }

    printf("test_gamelib OK: GameLib.SDL.h consumer API checks passed "
           "(version/color/collision/distance/random)\n");
    return 0;
}