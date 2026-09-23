# pdcurses 3.9 适配笔记（GLM-21，2026-09-13）

## 基本信息
- 上游: https://github.com/wmcbrine/PDCurses tag `3.9`
- 任务号: 7366（依赖活动 activity_id=6，外部候选导入自领取）
- 分支: `feat/pdcurses-3.9`；worktree: `~/qzy/GLM-21-pdcurses-3.9`
- 类型: C 库（多平台 curses 实现），SDL2 后端，静态库 `pdcurses.a`
- 依赖: `sdl2/2.32.10`（R35 实证：`conan list sdl2/* -r=ohpcd` 有 2.30.10/2.30.10.1/2.32.10，选最新 2.32.10）

## 后端选型（为什么是 SDL2）
PDCurses 3.9（wmcbrine 树）**没有无显示的 POSIX port**：仅提供 x11 / sdl1 / sdl2 / wincon / dos / os2 六种后端。
- x11：依赖 X11/Xaw/Xt——制品仓无 Xaw/Xt（libx11 存在但 curses 的 X11 port 还需 Xaw），且 OHOS 无 X11 运行环境；
- sdl1：制品仓无 sdl1；
- wincon/dos/os2：非 POSIX 平台 API；
- **sdl2：制品仓已发布（sdl2/2.32.10），且 SDL2 支持 `SDL_VIDEODRIVER=dummy` 无显示运行**——唯一可行路径。

## 配方要点
- sdl2 port 无 configure，直接 `make -C sdl2`：
  - 库目标 `all → libs → pdcurses.a`（`LIBEXE=$(AR)`，`LIBFLAGS=rcv`）；上游未实现动态库目标 → 配方 `options.shared=True` 直接 `ConanInvalidConfiguration`。
  - 核心对象规则 `$(BUILD) -c $<`（`BUILD=$(CC) $(CFLAGS) -I$(PDCURSES_SRCDIR)`），SDL 后端对象规则 `$(BUILD) $(SFLAGS) -c $<` → SDL2 头文件经 `SFLAGS` 注入，取自 conan 依赖 `sdl2` 的 cpp_info（component "SDL2" 的 include 与 include/SDL2）。
  - `CC`/`AR` 显式传（make 内建默认 `cc`/`ar` 会压过环境变量，R33 教训）：CC 取 profile `tools.build:compiler_executables.c`，AR 兜底 `llvm-ar`（profile 只钉了 c/cpp）。
  - 静态库不链接 SDL2（`make libs` 全程无链接），消费方自行链接 `-lpdcurses -lSDL2`。
- R26：curses 非系统同名库（OHOS 无 libcurses），静态库无 .so 污染问题。
- R33：不裸用 shell 环境变量——`generate()` 发 `VirtualBuildEnv`，编译器路径取 conf。
- 不构建 demos（交互式演示，无断言价值且拖长构建）。

## 上游测试账本（R51 四维，如实申报）
1. 上游静态声明总数 N_static = **0**：tag 3.9 无 test/ 目录、无 ctest/check/make test 目标、无测试框架；`demos/` 为交互式演示（firework/rain/testcurs/tuidemo/worm/xmas/ozdemo/ptest/sdltest），人工视觉检查、无断言。
2. 官方套件实际执行 N_executed = 0（无套件）。
3. 未执行/跳过 = 0。
4. 新增消费者测试 N_consumer = **1**（`test_package/test.c` → `test_probe`，4 个行为断言：initscr 非空、printw 接受格式化输出、timeout(0)+getch 无输入返回 ERR、endwin 返回非 ERR；SDL dummy 无显示驱动下真机执行）。

## 路径 B 判断
候选知识："无显示平台适配 curses/SDL 类 TUI 库：选 SDL2 后端 + SDL_VIDEODRIVER=dummy 无头消费者测试"。待 conan-verify 真实构建+测试通过后，做知识库查重（E 条目/适配检查清单），若确无同类条目再决定是否升 B（草稿 .kv+.md + draft-review + 知识库扩展 Issue）。当前按纯 A 推进，若不升 B 在汇报中说明理由。

## 验证记录
- （待 conan-verify 后回填）
---

**编译结束**: 2026-09-13 04:00
**最终状态**: built
