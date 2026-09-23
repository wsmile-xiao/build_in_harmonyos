// gamelib 1.9.9 — HarmonyOS-specific test (R02)
// 在 OHOS (aarch64) 工具链下编译运行，验证:
//   1) 平台宏 __OHOS__ 与 __aarch64__ 已定义（确认目标为 HarmonyOS aarch64 平台）
//   2) header-only gamelib 的 GameLib.SDL.h 在 OHOS 平台上真实调用公开 API
//   3) 公开静态 API 返回可观察且符合预期的结果（OHOS 运行期）
#include <cassert>
#include <cmath>
#include <cstdio>

#if !defined(__OHOS__)
#error "harmonyos_specific_test: __OHOS__ not defined — not compiled for HarmonyOS platform"
#endif
#if !defined(__aarch64__)
#error "harmonyos_specific_test: __aarch64__ not defined — not HarmonyOS aarch64 target"
#endif

#include "GameLib.SDL.h"

int main() {
    // 版本宏（OHOS 平台编译期）
    static_assert(GAMELIB_SDL_VERSION_MAJOR == 1, "version major mismatch (OHOS)");
    static_assert(GAMELIB_SDL_VERSION_MINOR == 9, "version minor mismatch (OHOS)");
    static_assert(GAMELIB_SDL_VERSION_PATCH == 9, "version patch mismatch (OHOS)");

    // 颜色宏（ARGB 格式）
    assert(COLOR_BLACK == 0xFF000000u);
    assert(COLOR_RGB(0, 128, 255) == 0xFF0080FFu);

    // 碰撞检测 / 距离 / 随机数（运行期真实调用）
    assert(GameLib::RectOverlap(0, 0, 8, 8, 4, 4, 8, 8) == true);
    assert(GameLib::RectOverlap(0, 0, 4, 4, 8, 8, 4, 4) == false);
    assert(GameLib::CircleOverlap(0, 0, 3, 2, 0, 3) == true);
    assert(GameLib::PointInRect(2, 2, 0, 0, 4, 4) == true);
    float d = GameLib::Distance(0, 0, 6, 8);
    assert(std::fabs(d - 10.0f) < 1e-5f);
    for (int i = 0; i < 50; i++) {
        int r = GameLib::Random(1, 10);
        assert(r >= 1 && r <= 10);
    }

    std::printf("harmonyos_specific_test OK: platform=OHOS(aarch64) __OHOS__/__aarch64__ defined, "
                "gamelib GameLib.SDL.h API runtime checks passed\n");
    return 0;
}