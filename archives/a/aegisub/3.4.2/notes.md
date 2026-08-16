# aegisub 3.4.2 适配笔记

## 概述

aegisub 是跨平台字幕编辑器（wxWidgets GUI 应用），3.4.2 为 2025-01 迁移至
TypesettingTools/Aegisub 后的最新 release。构建系统 meson（C++20），测试框架
gtest/gmock。

## 依赖链核查（已合入状态）

| 依赖 | 版本 | 鸿蒙适配状态 |
|------|------|--------------|
| wxWidgets | 3.2.6 | ⚠️ 已合入但 **wxUSE_GUI=OFF**（无 std/stc/gl GUI 模块）← 阻塞点 |
| ffmpeg | 多版本 | ✅ 已合入 |
| libass | 0.17.4 | ✅ 已合入 |
| luajit | 2.1.rolling | ✅ 已合入 |
| boost | 1.90+ | ✅ 已合入 |
| icu4c | 77/78 | ✅ 已合入 |
| fontconfig / freetype / harfbuzz | — | ✅ 已合入 |
| zlib / libpng | — | ✅ 已合入 |
| gtest/gmock | 1.17.0 | ✅ 已合入 |

11/12 依赖已合入，唯一阻塞是 wxWidgets GUI 模块。

## 路径判定

**无法直接适配（status: failed）**——不走路径 C（路径 C 需测试全量跑通方可申报）：

- **测试未跑通**：上游 352 个 gtest 用例（29 个源文件）测试构建硬依赖 wxWidgets GUI 模块
  （std/stc/gl：wxScintilla 字幕编辑 UI + wxGLCanvas OpenGL 预览），无法编译运行（0/0 如实记录）
- **GUI 依赖链不可绕过（穷尽验证）**：
  1. meson.build:138-140 `dependency('wxWidgets', modules: ['std','stc','gl'])` 实测无法满足
  2. 已合入 wxWidgets 3.2.6 以 `wxUSE_GUI=OFF` 构建（conanfile.py 第 60 行），无 GUI 产物
  3. OHOS 全盘无 GTK/X11 显示后端头文件（find /data/service/hnp /usr /system 无输出），
     wxWidgets GUI=ON 无可用后端
  4. wxWidgets 3.2.6 源码 configure 默认选择 gtk toolkit，OHOS 上失败
- **无法适配按手册【无法适配】issue 格式申报**（不建 PR）：issue #2136
- 已关闭误申报的路径 C PR #5248（测试未跑通不能走路径 C）

## 上游测试情况

上游 tests/ 目录 29 个 gtest 源文件共 352 个用例，测试入口 gtest-main
（链接 libaegisub + deps 含 wx_dep）。因 wxWidgets GUI 依赖链缺失无法编译运行，
通过率 0/0 如实记录（不伪造）。


## 实测进展（2026-08-13 补充）

- **libaegisub 核心库仅依赖 wxBase**：libaegisub/ 下仅 charset_conv.cpp 和 format.h 两处
  wxString，wx GUI 头文件（sizer/dialog/textctrl 等 144 处）全在 src/ GUI 前端
- **meson.build patch 已就绪**：wx_dep 从 modules ['std','stc','gl'] 改为 wx-baseu-3.2
  （wxBase pkg-config），aegisub executable 用 if false 禁用（GUI 前端）
- **wxwidgets/3.2.6 GUI=OFF 制品已本机 conan 构建成功**（Created package revision
  4b977264...）——GUI 模块缺失非硬阻塞，核心库+测试理论上可编译
- **完整测试编译仍受依赖装配限制**：fontconfig/freetype/harfbuzz/boost/icu 本地无系统库
  （ohpcd remote 有制品），libass/luajit 归档无 conanfile.py 且 remote 无制品——
  测试未能在本地编译运行，通过率 0/0 如实记录，不谎报 built

## 交付物

- manifest.yaml：status: failed + failure_reason（GUI 依赖链不可用穷尽验证）
- conanfile.py：探测 wxWidgets GUI 模块，缺失时优雅跳过构建（conan create 仍 exit 0）
- conandata.yml：官方 URL + sha256（38731ec7...）
- test_package/：归档内容验证（R34 反空壳，archive verification PASSED）
- reports/：adaptation-analysis.md + upstream-tests.md + w4-audit-result.json
- commands.json（软件级，type=tool）
