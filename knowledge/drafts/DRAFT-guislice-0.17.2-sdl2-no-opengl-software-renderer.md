# DRAFT: OHOS SDL2 无 OpenGL 后端 → GUI 库切软件渲染

> 草稿（路径 B：知识库扩展）——待审核 promote 为 E-entry。
> 来源库: guislice 0.17.2 | 作者: pc2-11 | 日期: 2026-09-21

## 问题

在 OHOS（HarmonyOS PC aarch64）上适配任何依赖 `sdl2` 的 GUI / 渲染 / 游戏库时，
`SDL_CreateWindow(... SDL_WINDOW_FULLSCREEN | SDL_WINDOW_OPENGL)` 必然失败：

```
ERROR: SDL_CreateWindow(): OpenGL support is either not configured in SDL
or not available in current SDL video driver (dummy) or platform
```

## 根因

ohpcd 制品仓发布的 `sdl2` 配方（见 `archives/s/SDL2`，E092）在 OHOS 平台关闭了
X11/Wayland/KMSDRM/OpenGL/OpenGLES 等全部平台视频后端，仅保留 dummy/offscreen。
因此：
- 请求 OpenGL 上下文（`SDL_WINDOW_OPENGL`）→ 创建窗口失败；
- 请求加速渲染器（`SDL_RENDERER_ACCELERATED`）→ 无后端可用；
- 上游 GUI 库默认按桌面假设走 OpenGL 路径 → 初始化即失败。

## 方案（三层适配 + 两个叠加修复）

1. **配置层**：新增 OHOS 专用配置头（仿上游示例 config），把渲染后端切软件：
   `#define DRV_SDL_RENDER_ACCEL 0`（本库同时 `DRV_DISP_SDL2`/`DRV_TOUCH_SDL`）。
2. **驱动层**：把 `SDL_WINDOW_OPENGL` 标志按配置条件化——
   `#if (DRV_SDL_RENDER_ACCEL)` 才带 OpenGL 标志，软件模式不带
   （复用库自身的渲染开关，不引入 `__OHOS__` 平台宏，R8 合规）。
3. **运行时**：headless CI / 无显示环境用 `SDL_VIDEODRIVER=dummy`（或 offscreen）
   运行自检与消费者用例；`SDL_VIDEODRIVER=dummy` 下软件渲染探针实测可用。
4. **叠加修复 A（上游自检程序）**：`test_sdl2.c` 同样去掉 OpenGL 窗口标志、
   改 `SDL_RENDERER_SOFTWARE`，使上游 SDL 自检可在 OHOS headless 运行。
5. **叠加修复 B（变参宏空参）**：库的调试宏 `GSLC_DEBUG_PRINT(sFmt, __VA_ARGS__)`
   空参调用（`GSLC_DEBUG_PRINT("...\n")`）展开为 `gslc_DebugPrintf(sFmt,)`
   尾逗号语法错（clang 15 报 `expected expression`），补空串实参
   `GSLC_DEBUG_PRINT("...\n","")`（仅该库一处单例）。

## 验证

- 22 个编译单元（GUIslice.c + elem/*.c + GUIslice_drv_sdl.c）OHOS clang15 0 错误；
- 上游 `test_sdl2` headless 运行通过（rc=1 为其设计成功码）；
- 消费者用例（test_package test.c）：仅用公开头文件/静态库调用 `gslc_Init`（SDL2
  软件渲染）、页面/元素创建、页面切换、绘制与更新循环，14/14 断言通过；
- conan-verify G1-G4 全过；W3 L0/L1 通过（Pass rate 100%）。

## 适用边界 / 反例

- 适用：基于 ohpcd sdl2 的 GUI/渲染/游戏库的 OHOS 适配；headless CI。
- 反例：SDL2 自带 `SDL_CreateWindow` 但走软件渲染的普通库无需改驱动；
  OHOS 若有专用显示后端（未来 SDL2 配方启用 KMS/自研驱动）则此约束解除。
- 扩展（r02 全量测试返工验证）：
  - SDL1-only API（如 `SDL_EnableKeyRepeat`）在 SDL2 配置下须按上游互斥分支守卫
    （`#if defined(DRV_DISP_SDL1)`），SDL2 以 `SDL_KEYDOWN event.repeat` 原生交付按键重复——
    上游示例如 ex22 未做版本守卫，需最小补丁，不改变语义（补丁 0003）。
  - 依赖 SDL1 的测试/示例在 OHOS 的纳入路径：ohpcd 无原生 `sdl/1.2.15`，但
    `sdl12-compat/1.2.68`（SDL1 API 兼容层，libsdl-org 官方）+ `sdl_ttf/2.0.11`
    已发布，可经其实例化并 headless 运行 SDL1 入口（test_sdl1 实测 rc=0）——
    不得以"无 SDL1 配方"直接跳过运行（r01 教训）。

## 查重关系

- `similar_to`: E472（SDL dummy headless 测试签名，test_package 测试侧，部分覆盖）
- `caused_by`: E092（OHOS SDL2 配方关闭 OpenGL 后端）
- `combined_with`: E466/E195（init-build 嵌套源码误提升，本库单独走 reports 台账）

## 决定

- `new_draft`：候选 1（可跨库复用）→ 本草稿
- `reuse_existing`：候选 2 引 E466/E195；候选 3/4 记 notes.md，不建草稿
- 路径：B（知识库扩展）
- r02 复核：候选 5（SDL1-only API 互斥分支守卫）与候选 6（sdl12-compat 纳入 SDL1
  入口）的边界差异已并入上文"适用边界/反例·扩展"，保持 .kv/.md 同 stem 配对；
  详细台账见 archives/g/guislice/0.17.2/reports/knowledge-candidate-ledger.md