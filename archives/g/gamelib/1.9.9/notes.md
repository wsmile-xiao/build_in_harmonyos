# gamelib 1.9.9 适配笔记

## 编译环境
- 构建系统: header-only（上游无库级构建系统，仅 examples/Makefile 编译示例）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15 (OHOS aarch64)
- 状态: built

## 库结构
- `GameLib.h` — Win32 GDI 后端（Windows 专用，零外部依赖，含 `<windows.h>`/`<mmsystem.h>`）
- `GameLib.SDL.h` — SDL2 跨平台后端（Windows/Linux/macOS/Web/OHOS）
- OHOS 适配采用 `GameLib.SDL.h`，依赖 `sdl2/2.30.10`（已发布 ohpcd）

## 编译步骤
1. `init-build gamelib 1.9.9 --url=https://github.com/skywind3000/GameLib/archive/refs/tags/1.9.9.tar.gz`
   - 注意：直接传仓库主页 URL（无 tar 后缀）会下载到 HTML；必须使用 `archive/refs/tags/1.9.9.tar.gz` 官方归档 URL。
2. 官方 tag 核验：`1.9.9` = f17661a (2026-05-05)，tarball SHA-256 = `2d99c0b4f70323d894a17ecb45b84d5cdff167b017a6ba02b77d0244080136e5`
3. lang-preflight: cpp ✅
4. 编写 conanfile.py（header-library）+ conandata.yml + test_package/（消费者测试 + 鸿蒙专项测试）
5. 无 patches：header-only 库，SDL2 后端在 OHOS 上无需源码修改

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 报"下载内容是 HTML" | URL 传了仓库主页而非归档 | 使用官方 `archive/refs/tags/1.9.9.tar.gz` URL |
| 2 | /tmp 只读 | OHOS 平台 /tmp 只读（E002） | 使用 `$TMPDIR`（~/tmp）下载与解压 |

## 依赖版本
- sdl2/2.30.10（requirements，transitive_headers/transitive_libs）

## 验证结果
- test_package: 消费者测试 test_gamelib（版本/颜色宏/碰撞检测/距离/随机数）+ harmonyos_specific_test（__OHOS__/__aarch64__ 平台宏 + API 运行期断言），conan create 阶段 2/2 实测通过
- 上游 tests/ 目录: 3 个示例程序（demo1.cpp / demo_scene_save.cpp / sdldemo1.cpp），非测试框架用例
- 上游测试双口径统计（完整台账见 reports/test-report.md，PR 内摘要如下）:
  - source_declared_total=21（tests/ 3 + examples/ 18，官方 tag 全部 .cpp 程序）
  - configured_executable_total=17（16 个 SDL 后端示例 + sdldemo1 修复上游调用后）
  - executed_passed_total=16（16/16 SDL 示例编译通过并无头运行正常；演示程序非独立用例，不计入通过率分母）
  - 未运行/未实例化=5：demo1/demo_scene_save/demo_win（Win32 GDI 平台限制，windows.h 缺失）、demo_sdl_mixer（需可选 SDL2_mixer 扩展）、sdldemo1（上游调用错误 DrawTextScale 5 参 vs 6 参）
  - 当前 OHOS 配置可执行集合通过率: 16/16 (100%)；全量通过率口径: 演示程序不按独立用例计

## 注意事项
- GameLib.h 与 GameLib.SDL.h 不能出现在同一翻译单元（内部 #error 守卫）
- SDL2_image/ttf/mixer 为可选扩展，__has_include 自动探测；本配方未强制依赖，缺省时自动降级核心能力
- 构建产物仅头文件（无 .a/.so/可执行文件），不产生 commands.json（R38 仅 CLI 需要）
---

**编译结束**: 2026-09-20 09:45
**最终状态**: built
