# guislice 0.17.2 适配笔记

## 编译环境
- 构建系统: makefile（GUIslice 无顶层 configure/CMake，Linux 构建入口为 examples/linux/Makefile，直接编译 src/ 库核心 + SDL2 驱动）
- 编译日期: 2026-09-21
- 编译器: clang/clang++（OHOS SDK 15.0.4，triplet aarch64-linux-ohos）
- 状态: built

## 编译步骤
1. init-build guislice 0.17.2（官方 v0.17.2 tag tarball，sha256 c6d2ddc1...eb713）
   - ⚠️ 嵌套源码检测误判：examples/linux 是唯一含 Makefile 的子目录，被提升为源码根，
     真实库源码 src/ 丢失 → 手动重建 .orig/.work（tar --strip-components=1 + .tarball-sha256，
     cp -a 不用硬链接，HMDFS 禁硬链接）
2. lang-preflight: cpp 匹配（c:48, cpp:10）
3. 直编验证：src/GUIslice.c + src/elem/*.c + src/GUIslice_drv_sdl.c（22 编译单元）
   用 -DUSER_CONFIG_LOADED -DUSER_CONFIG_INC_FILE -DUSER_CONFIG_INC_FNAME=ohos-sdl2-default.h
   选择 OHOS SDL2 软件渲染配置
4. 上游 test_sdl2 编译并 headless 运行（SDL_VIDEODRIVER=dummy，rc=1 设计成功码）
5. conan-init → conan-verify（G1-G4 全过）→ finish/W3（Pass rate 100%）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SDL_CreateWindow 带 SDL_WINDOW_OPENGL 失败 | ohpcd sdl2 配方无 OpenGL 后端（E092），仅 dummy/offscreen | 配置 DRV_SDL_RENDER_ACCEL=0 + 驱动按该开关条件化窗口标志（补丁 0002） |
| 2 | GSLC_DEBUG_PRINT 空参调用编译错误 | 变参宏展开为 gslc_DebugPrintf(sFmt,) 尾逗号 | 补空串实参 GSLC_DEBUG_PRINT("...","")（补丁 0002） |
| 3 | test_sdl2 上游自检失败 | 同上 OpenGL 窗口标志 | 补丁 0001 去 OpenGL 标志 + 软件渲染器 |
| 4 | init-build 误把 examples/linux 当源码根 | _promote_nested_source 仅找构建标记，根目录无 Makefile | 手动重建 .orig/.work（详见 reports/knowledge-candidate-ledger.md 候选 2，E466/E195 扩展） |
| 5 | gslc_InitDebug 回调签名导致异常 | GSLC_CB_DEBUG_OUT 是 int16_t(*)(char) 逐字符回调 | 消费者测试按签名实现 DebugOut(char) |

## 源码修改
- patches/0001-examples-linux-test_sdl2.c.patch: 去 OpenGL 窗口标志、SDL_RENDERER_SOFTWARE
- patches/0002-src-GUIslice_drv_sdl.c.patch: SDL_WINDOW_OPENGL 按 DRV_SDL_RENDER_ACCEL 条件化；
  GSLC_DEBUG_PRINT 空参修复
- conanfile.py build() 内生成 configs/ohos-sdl2-default.h（软件渲染配置，避免新增文件补丁格式问题）

## 依赖版本
- sdl2/2.30.10（ohpcd 已发布）
- sdl2_ttf/2.24.0（ohpcd 已发布，传递依赖 freetype/2.14.3.1）

## 验证结果
- 22/22 编译单元 0 错误
- test_sdl2 headless 运行通过（rc=1）
- 消费者用例 test_package/test.c：14/14 断言通过（gslc_Init、页面/元素/页切换/绘制/更新）
- conan-verify G1-G4 PASS；W3 L0/L1 PASS（Pass rate 100%）
- W3 命中其他库基线垃圾（cloog/.build-closed、cloog/.staging-verified、kics/.staging-verified）：
  记录隔离前 SHA-256（e3b0c442... 空文件）、临时隔离复跑、原样恢复核对一致；单包口径
  JUNK_PR_DIFF=pr.diff 下 JC pass

## 注意事项
- 消费者使用库需带配置选择宏：-DUSER_CONFIG_LOADED -DUSER_CONFIG_INC_FILE
  -DUSER_CONFIG_INC_FNAME="ohos-sdl2-default.h"（该头随包安装于 include/guislice/）
- OHOS 无显示环境运行需 SDL_VIDEODRIVER=dummy / SDL_AUDIODRIVER=dummy
- 知识草稿: knowledge/drafts/DRAFT-guislice-0.17.2-sdl2-no-opengl-software-renderer.{kv,md}

**编译结束**: 2026-09-21 01:07
**最终状态**: built
---

**编译结束**: 2026-09-21 21:57
**最终状态**: built
