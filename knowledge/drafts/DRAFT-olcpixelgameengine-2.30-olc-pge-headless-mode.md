# E-DRAFT: 无原生窗口后端的图形/游戏引擎库在 OHOS 使用上游无头编译模式（编译宏）而非自写窗口后端

- **触发实例**：olcpixelgameengine 2.30 适配（2026-09-29，分支 feat/olcpixelgameengine-2.30）
- **错误签名**：
  - 无头模式未启用时：`X11/X.h: No such file or directory` / `Xlib.h: No such file or directory`
    （`__linux__` 自动选中 `OLC_PLATFORM_X11`，OHOS sysroot 无 X11 头）
  - header-only 配方误标 `package_type = "library"`：`Package type is 'library', but no 'shared' option declared`
  - 未知 API 假设：`no member named 'Resize' in 'olc::Sprite'`（2.30 无 Resize，用 GetPixel/Sample）
- **类别**：ohos-graphics-headless-mode（OHOS 图形库无头模式类）
- **严重度**：2（编译期确定性，处置模式固定）

## 症状

单头文件游戏引擎 olcPixelGameEngine 2.30（one header C++17，OLC-3 许可）在 OHOS aarch64
上按默认方式包含头文件时编译失败——上游平台选择代码只覆盖 Win32/X11/GLUT/Emscripten，
OHOS 上 `__linux__` 自动选 X11 后端，而 OHOS sysroot 没有 X11 头。

## 根因

OHOS PC 无原生窗口后端（E471 同款平台事实）。上游对窗口后端的支持仅限 Win32/X11/GLUT/
Emscripten；直接编译必然缺头或无平台可选。但上游自带了**真正的无头模式**
（`OLC_PGE_HEADLESS` → `OLC_PLATFORM_HEADLESS`/`OLC_GFX_HEADLESS`/`OLC_IMAGE_HEADLESS`，
是上游实现的 Platform_Headless/Renderer_Headless，非空壳 stub）。适配的正确姿态是
"用上游无头编译模式"，而不是自写 OHOS 窗口后端、加运行时 dummy 驱动或把上游显示测试
改分类。

## 处置（不改上游头文件、不加补丁）

1. **配方**：`package_type = "header-library"`（不能是 `"library"`——Conan 2 要求 library
   声明 shared option，否则报 `no 'shared' option declared`）；`copy()` 目标必须用
   `os.path.join(self.package_folder, "include")` 绝对路径（相对 `dst` 在 basic_layout 下
   会解析到 build 目录导致 `WARN: No files in this package!`）；`package_id()` 里
   `self.info.clear()`。
2. **消费方式**：消费方编译单元先 `#define OLC_PGE_HEADLESS` 再 `#define OLC_PGE_APPLICATION`
   再 `#include "olcPixelGameEngine.h"`（test_package CMakeLists 用
   `target_compile_definitions` 传入），C++17。
3. **验证**：
   - test_package 消费者用例：无头模式调用公开 API（Sprite 像素读写/无头 Construct/Pixel
     颜色），`ctest 1/1 Passed`；
   - test_ohos 鸿蒙专项测试：OHOS 工具链直接编译运行（Sprite 渐变填充/GetPixel 采样、
     无头 Construct、vi2d 运算、Pixel 常量），5 项断言 failures=0；
   - 上游源码零修改；OLC_PGE_HEADLESS 下 9 条 missing-override 告警为上游原样
     （`-Winconsistent-missing-override`），如实记录为上游保真噪声。

## 验证

```bash
/data/service/hnp/bin/clang++ -std=c++17 -O2 -fPIC -I<src> -pthread test_ohos/ohos_pge_test.cpp -o ohos_pge_test
./ohos_pge_test
# OHOS_TEST sprite(0,0)=0xFFFF0000 sprite(63,63)=0xFFFFFCFC / construct_rc=1(OK) /
# vi2d=(4,5) / pixel=0xFF0000FF → OHOS_TEST_RESULT failures=0
```

## 适用边界

- **适用**：上游自带真实无头/离屏编译模式的窗口化图形库、游戏引擎（单头文件 C++17 类），
  OHOS 无对应窗口后端时；以及 header-only 图形库的 Conan 2 打包（header-library + 绝对
  copy 目标 + 消费方宏定义）。
- **反例**：上游**没有**无头模式时（如 raygui 需宿主后端），不得伪造 stub 后端或空壳
  Platform——必须写真实后端或按 E471 分类显示依赖测试并加无显示 API 探针（raygui
  DRAFT-7353 教训）；库本体不得用 `-Wno-error` 掩盖问题。

## 查重（七轴）

- complete/exact：无
- causal_duplicate：无（E471/E464/E472 均无"上游编译期无头宏"这一机制）
- trigger_overlap：部分（OHOS 无原生显示/窗口后端 → 图形库需无头路径，与 E471/E464/E472 同源）
- solution_overlap：部分（"无头验证"思路一致；机制不同：编译期宏 vs E464 运行时 dummy
  资源注册 vs E472 环境 dummy 驱动(SDL_VIDEODRIVER=dummy) vs E471 测试分类+探针）
- combination_novelty：是（单头文件游戏引擎 + 上游原生 HEADLESS 编译宏 + Conan header-only
  打包 + 消费方宏定义 的组合）
- boundary_novelty：是（边界：仅当上游自带真实无头模式；反例：无无头模式须写后端/分类）
- test_migration_novelty：是（鸿蒙专项测试直接 OHOS 工具链编译运行无头引擎用例；消费者
  用例以宏定义消费）

## 关系

similar_to E471（OHOS 无显示后端）、similar_to E464（mygui headless 验证）、
similar_to E472（SDL dummy headless 测试）；核对引用 E257（header-only G1 build() 门禁）、
E321（header-only Conan2 header-library 打包）

## 决定

**new_draft（路径 B）**——部分覆盖 E471/E464/E472 且存在已由真实日志（本任务 test_ohos/
test_package 运行证据）验证的新增差异，可跨库复用（适用于其它自带无头模式的窗口化
图形/引擎库）。配方相关的 G1/header-library 问题分别复用 E257/E321，不另建草稿。