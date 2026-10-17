# DRAFT: 单文件 C 图形库（tigr 类）适配 OHOS 的官方 headless 编译模式

> 配对 KV: `DRAFT-tigr-3.1.0-single-file-graphics-headless-compile.kv`
> 来源 PR 素材: tigr 3.1.0 第一轮适配（pc2-33，task tigr-3.1-r01-pc2-33-20260916T153205Z）
> 状态: DRAFT（待评审提升为 E-entry）

## 问题

单文件 C 图形库（如 erkkah/tigr，整个库即 `tigr.c`+`tigr.h`）在 OHOS 上按
默认配置编译时，命中 `__linux__ && !__ANDROID__` 平台分支，include
`X11/X.h`、`GL/gl.h`、`GL/glx.h`；OHOS 无 X11/GLX 头文件与窗口后端，编译
直接失败：

```
fatal error: 'X11/X.h' file not found
#include <X11/X.h>
```

## 根因

tigr 是跨平台单文件库，窗口/输入/OpenGL 渲染后端按平台宏分开编译
（`tigr_win.c`/`tigr_linux.c`/`tigr_gl.c` 等）。OHOS 的 clang 定义
`__linux__=1` 且不定义 `__ANDROID__`，因此落入 Linux 分支需要 X11+GLX——
而 OHOS 没有这两者。核心 framebuffer（位图、绘制原语、文字、PNG 读写、
内置 inflate）本身是纯 C、无平台依赖，只是被窗口后端拖累。

## 方案

使用上游官方提供的 `TIGR_HEADLESS` 编译宏（`tigr.c` 中以
`#ifndef TIGR_HEADLESS` 守卫整个窗口/输入/GL 实现段）：

```bash
clang -DTIGR_HEADLESS -fPIC -O2 -I<src> -c tigr.c
llvm-ar rcs libtigr.a tigr.o
```

- 保留：`tigrBitmap/tigrClear/tigrPlot/tigrLine/tigrRect/tigrFillRect/
  tigrCircle/tigrFillCircle/tigrBlit*/tigrClip/tigrGet/tigrResize/
  tigrPrint/tigrTextWidth/tigrTextHeight/tigrLoadImage/tigrSaveImage/
  tigrInflate/tigrReadFile/tigrDecodeUTF8` —— 全部实质实现，无 stub。
- 剔除：`tigrWindow/tigrUpdate/tigrEvents/tigrClosed/tigrKeyDown` 等
  窗口/输入/GL API（上游官方设计，headless 即为此类无窗口平台提供）。

Conan 配方配套三要素（与 E392 一致，此处合并记录）：

1. **codeload BadZipFile**：`get()` 显式
   `src["filename"]="<name>-<ver>.tar.gz"` 纠正编码器误选。
2. **compiler_executables 是 dict**：整取
   `self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)`
   再 `.get("c","clang")`，不能当作列表项读取。
3. **raw makefile 场景**：`self.run` 要确保 cwd 正确（tigr 无 Makefile
   构建目标，直接 `cc -c tigr.c` + `ar rcs`）。

## 验证

| 项 | 结果 |
|----|------|
| conan create（OHOS aarch64, clang 15.0.4） | ✅ 通过 |
| test_package 消费者测试（test_tigr，15 断言，动态计数） | ✅ ALL 15 CHECKS PASSED |
| 鸿蒙专项测试（test_tigr_ohos，13 断言：平台宏/小端布局/inflate/64 位） | ✅ ALL 13 OHOS CHECKS PASSED |
| W3 本地 CI（finish step5: setup.sh + build_and_test.sh L0-L5） | ✅ 100% (1/1) |
| 上游 headless 冒烟样例 | ✅ exit 0，产出 headless.png 320x240 |
| 上游 ci/ci.c（R03 headless 迁移版，配方 build() 内运行） | ✅ Create offscreen/Drawing API/Unicode 全 OK，`*** All tests pass OK`，exit 0 |

上游唯一独立测试 ci/ci.c：R01/R02 因 X11+GL 窗口后端 OHOS 编译即失败
（`X11/X.h not found`），按双口径如实上报 0/1；**R03 以最小补丁
（patches/0001-ci-headless-guard.patch，#ifndef TIGR_HEADLESS guard 剔除窗口/
GL/输入路径，补丁前后 SHA-256：900514f4… → f32b8b3d…）迁移为 headless 构建
并实测运行通过 → 双口径提升为 source_declared_total=1、configured_
executable_total=1、executed_passed_total=1、全量通过率 **1/1 (100%)**，
source_declared 不改写；功能覆盖另由鸿蒙专项 + 消费者测试全部实际验证。

## 适用边界

- ✅ 单文件 C 图形/多媒体库（tigr、stb 系、dr_libs 族），或无窗口宏的框架库
- ✅ 无 X11/GLX 的 OHOS / 嵌入式 / 服务器平台
- ⚠️ 需要真实窗口/输入的库不可用此方案（改用 E463/E464/E471/E472 运行时探测类方案）
- ❌ 库无官方 headless 宏时不可强行剥离（会变 stub，违反 R40）

## 查重差异

- 与 E463（GTK Broadway headless consumer）/E464（mygui dummy resource）/
  E471（display test classification）/E472（SDL dummy driver）：方案类别不同
  ——既有条目是**运行时探测/假驱动**，本条目是**编译期官方宏剥离**；场景
  不同（单文件小库 vs 大型框架），组合起来覆盖无窗口适配的两种手段。
- 与 E392（raw makefile Conan 配方三陷阱）：部分重叠（配方要素），但
  E392 不覆盖「单文件图形库 headless 编译模式」这一适配策略本身。
- 与 E195/E466（嵌套源码提升误判）：无关，tigr 的 init-build 误判已按
  既有知识恢复，不作为新增。

## 反例

- 直接把窗口函数改名保留（stub）→ 违反 R40，且消费者链接会得到空实现。
- 不显式 filename 直接用 codeload URL → BadZipFile（已实测）。
- 用 `== "Linux"` 判断 settings.os → OHOS 不命中，配方不可用（R32）。

## 关系

- similar_to: E392（raw makefile 配方）、E463/E464/E471/E472（headless 适配家族）
- caused_by: OHOS 无 X11/GLX 窗口后端
- prerequisite_of: 消费者验证（headless 位图/PNG 用例）
- conflicts_with: R40 若退化为 stub 时；与运行时探测方案不冲突（互补）

## 关键文件

- `archives/t/tigr/3.1.0/conanfile.py`（TIGR_HEADLESS + filename + dict 编译器）
- `archives/t/tigr/3.1.0/test_package/test_tigr_ohos.c`（鸿蒙专项 4 断言）
- `archives/t/tigr/3.1.0/test_package/test_tigr.c`（消费者 8 断言）
