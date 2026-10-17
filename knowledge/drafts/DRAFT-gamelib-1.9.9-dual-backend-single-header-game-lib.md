# DRAFT: 双后端单头文件游戏库（gamelib 类）适配 OHOS 的知识沉淀

> 配对 KV: `DRAFT-gamelib-1.9.9-dual-backend-single-header-game-lib.kv`
> 来源 PR 素材: gamelib 1.9.9 第一轮适配（pc2-4，task gamelib-1.9.9-r01-pc2-4-20260919T124859Z）
> 状态: DRAFT（待评审提升为 E-entry）

## 问题

单头文件游戏库（如 skywind3000/GameLib，整个库即 `GameLib.h` + `GameLib.SDL.h`
两个头文件）在 OHOS 上的适配，第一个"错误"不是编译失败，而是**产品线选择**：

- `GameLib.h` 是 Win32 GDI 后端，`#include <windows.h>` / `<mmsystem.h>`；
  OHOS/Linux 无这些头文件，该产品线在非 Windows 平台**不可编译**——这是
  产品线边界，不是配方缺陷，不能靠打补丁"修好"。
- `GameLib.SDL.h` 是 SDL2 跨平台后端（Windows/Linux/macOS/Web/OHOS），
  依赖 `sdl2`（必需）与 `SDL2_image/ttf/mixer`（可选，`__has_include`
  自动探测，缺失时自动降级为纯 SDL2 核心能力）。

第二个问题是**无窗口环境下的测试**：窗口型游戏库的 `Open()/Update()`
在 CI/无头环境无法真实运行；需要找到不依赖窗口的公开 API 做消费者断言。

## 根因

1. 单头文件库可能同时维护多条产品线（Win32 GDI 与 SDL2 各一个头文件，
   头文件内部用 `#error` 防止同一翻译单元混用）。OHOS 适配必须选择
   跨平台 SDL2 产品线，并在交付中如实声明 Win32 产品线的平台边界。
2. `GameLib.SDL.h` 在头文件顶层 include `<SDL.h>`，下游消费者编译时必须
   能直接找到 SDL2 头文件与库 → 配方 requirements 必须带
   `transitive_headers=True, transitive_libs=True`。
3. 上游无库级构建系统（仅 examples/Makefile 编译演示），配方按
   header-only 打包两个头文件，无编译产物（R38 不适用）。
4. 上游测试入口（tests/ + examples/ 共 21 个 .cpp）全部是**演示程序**
   （游戏窗口循环），无 TEST_CASE/ctest/GTest 注册；其中 3 个是 Win32
   专有（demo1/demo_scene_save/demo_win，include GameLib.h），OHOS 不可编译。

## 方案

### 1. 产品线选择（核心）

识别库的多产品线头文件 → 确认 OHOS 可用产品线：

| 产品线 | 后端 | OHOS 可用性 | 处置 |
|--------|------|------------|------|
| GameLib.h | Win32 GDI | ❌（windows.h 缺失） | 照常打包进 include/（供 Windows 下游），如实声明平台边界 |
| GameLib.SDL.h | SDL2 | ✅ | 作为 OHOS 主产品线，test_package 实测 |

### 2. Conan 配方（header-only + sdl2 transitive）

```python
package_type = "header-library"
def requirements(self):
    self.requires("sdl2/2.30.10", transitive_headers=True, transitive_libs=True)
def package(self):
    copy(self, "GameLib.h", src, include)
    copy(self, "GameLib.SDL.h", src, include)
    copy(self, "LICENSE", src, licenses, keep_path=False)
def package_info(self):
    self.cpp_info.bindirs = []
    self.cpp_info.libdirs = []
```

要点：
- 可选扩展（SDL2_image/ttf/mixer）**不**进 requirements——头文件 `__has_include`
  自动降级，配内置 `GAMELIB_SDL_DISABLE_*` 关闭宏，由下游按需选择。
- 官方归档 URL 用 `archive/refs/tags/X.Y.Z.tar.gz`，**不要**用仓库主页 URL
  （主页 URL 会让 init-build 下载到 HTML，报"下载内容是 HTML"）。

### 3. test_package：静态纯逻辑 API 无窗口断言

窗口型游戏库在无显示环境下用**公开静态 API**（不依赖窗口/渲染器实例）做
运行期断言，验证"第三方使用者能编译、链接、调用并得到可观察结果"：

- `GameLib::RectOverlap / CircleOverlap / PointInRect / Distance / Random`
- 颜色宏 `COLOR_RGB / COLOR_ARGB / COLOR_BLACK...`、版本宏
  `GAMELIB_SDL_VERSION_*`
- 鸿蒙专项测试：`__OHOS__` / `__aarch64__` 平台宏 + 上述 API 运行期断言

### 4. 上游测试台账

21 个 .cpp 全列台账，逐项标注"是否独立上游用例 = 否（演示程序）"、
分类理由、实际运行情况；Win32 专有入口如实列平台限制不可编译；上游缺陷
（sdldemo1 的 `DrawTextScale` 5 参调用 vs 6 参声明）如实记录。

## 验证

- `conan create` G2 PASS（含 test_package 2/2：test_gamelib + harmonyos_specific_test）
- conan-verify G1-G4/L2/L4/L5 全 PASS
- W3 本地 CI：L0 pass（.ci-result.json exit_code=0）
- 16 个 SDL 示例用 OHOS 工具链 + conan sdl2 编译通过，`SDL_VIDEODRIVER=dummy`
  无头运行正常启动
- 关键命令：
  ```
  conan create archives/g/gamelib/1.9.9 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
  ./test_package/build/clang-15-armv8-17-release/test_gamelib
  ./test_package/build/clang-15-armv8-17-release/harmonyos_specific_test
  ```

## 适用边界

- 适用：多产品线/双后端单头文件库（Win32+SDL2 等）；任何窗口型游戏/UI 库
  需要无窗口消费者测试的场景；带可选扩展自动探测的头文件库。
- 不适用：仅窗口后端且无跨平台产品线、也无官方 headless 编译宏的库
  （参照 E463/E471/E472 运行时探测方案）；需要真实渲染/音频行为验证的场景。
- 反例：不能把"Win32 产品线不可编译"写成当前库适配失败——产品线选择是
  适配决策，不是阻塞；不能为凑通过率把演示程序当独立测试用例。

## 查重差异（与 DRAFT-tigr 对比）

- DRAFT-tigr：单文件 **C** 库，官方 `TIGR_HEADLESS` **编译宏**剔除窗口后端，
  保留 framebuffer 核心——编译期宏方案。
- 本条目：单头文件 **C++** 库，**多产品线头文件选择**（SDL2 产品线）+
  **transitive sdl2** + **静态纯逻辑 API 无窗口断言**——产品线选择方案。
- 两者互补：无头编译宏 / 产品线选择都是"无窗口平台用可移植核心"的实例，
  但触发点、配方形态、测试模式不同，各自成立。

## R02 扩展：上游测试调用与头签名漂移的最小补丁纳入（2026-09-20 实测）

单头文件库上游测试（demo/tests .cpp）可能与发布头文件签名漂移：上游
sdldemo1.cpp 以 `DrawTextScale(84,96,"SDL DEMO 1",COLOR_WHITE,2)`（5 参）调用，
而 1.9.9 声明为 6 参 `(x,y,text,color,w,h)`，编译报
`too few arguments to function call, expected 6, have 5`。

处置（实测通过，纳入 21/21 台账）：
1. 以当前库允许范围内的**最小补丁** `patches/0001-fix-sdldemo1-drawtextscale-call.patch`
   修复调用（补全缺失参数为 6 参，与同类 demo_sdl.cpp 语义一致）；
   记录修复前后 SHA-256（`bb433c4d…`→`d4e7d66e…`）。
2. 注册到 conandata.yml `patches:` 列表（patch_type: portability），
   conan create（G2）内置 patcher 正常应用（日志见 "Apply patch (portability)"）。
3. 同一问题在 demo_scene_save.cpp 迁移版中出现 2 处，一并修复。
4. **G0 clean-verify 平台限制**：本地 G0 用系统 `patch`（toybox 0.8.12）对
   CRLF 行尾源文件应用 LF 补丁报 `Hunk 1 FAILED`/`Removing DOS newlines`；
   CI 实际路径是 conan create 的内置 patcher（G2 PASS），G0 属非阻塞清洁验证，
   记录为平台限制，不阻塞交付。

## R02 扩展：Win32 专有演示程序迁移到 SDL2 等价版（实测通过）

多产品线库的演示程序可能只链接 Win32 产品线（`#include "../GameLib.h"`，
依赖 windows.h/mmsystem.h），OHOS 不可编译。迁移处置（已授权）：

1. 复制原入口为适配版（`migrated-sdl-tests/`），仅切换
   `#include "../GameLib.h"` → `#include "../GameLib.SDL.h"`——两后端 API 同构，
   逐 API 核对无 Win32 专属调用（LoadSprite/CreateTilemap/SetTile/FillTileRect/
   GetDeltaTime/GetTime/ShowFps/SetClip/AspectLock/LoadInt… 均在 SDL 头存在）。
2. 迁移版编译 exit 0、`SDL_VIDEODRIVER=dummy` 无头运行 exit 124 正常。
3. 台账与 PR 如实单列"原入口 → 适配版入口"映射与改写范围（头文件切换 +
   偶发同款签名修复），**不得把改写版伪写为上游原样用例**。

## R02 扩展：可选扩展依赖的测试入口纳入（实测通过）

依赖可选扩展（SDL2_mixer）的测试入口首次判定与最终回报前都要用
`conan download "sdl2_mixer/*" -r=ohpcd --only-recipe` 实测 registry；
已发布（2.8.1/2.8.2）即恢复配置（`-lSDL2 -lSDL2_mixer`）构建并实际运行，
不得沿用旧 skip 结论；实测编译 exit 0、无头运行 exit 124 正常。
