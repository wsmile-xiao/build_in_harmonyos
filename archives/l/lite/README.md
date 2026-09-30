# lite (Lite XL)

Lite XL 是一个用 Lua + C 编写的轻量、快速、开源的文本编辑器，致力于在保留
高效编辑体验的同时提供极低的内存占用与流畅响应。它是知名编辑器 lite 的社区
活跃分支（上游项目：https://github.com/lite-xl/lite-xl）。

## 功能概述

- 轻量快速：核心用 C 编写，启动与响应速度快
- 可扩展：内嵌 Lua 5.4 运行时，插件与配置全部用 Lua 编写
- 现代化界面：基于 SDL3 + FreeType2 渲染，支持 GPU 加速
- 跨平台：Linux / macOS / Windows / BSD / 鸿蒙（本适配目标）

## 构建信息

| 项 | 值 |
|----|-----|
| 版本 | 2.1.8 |
| 构建系统 | meson |
| 许可证 | MIT |
| 产物 | `bin/lite-xl`（GUI 应用）+ `share/lite-xl/`（运行时数据） |
| 包类型 | application（R38：软件级 `commands.json` 已声明） |

## 依赖

- sdl3/3.4.8（上游 2.1.8 源码硬编码 `dependency('sdl3', static: true)`，**无 sdl2 回退**；
  sdl3/3.4.8 conan 配方由协作者并行补全，本配方 requires 已指向它）
- freetype/2.14.3（pkg-config 名 freetype2）
- lua/5.4.8（`use_system_lua=true`，pkg-config 名 lua-5.4 + lua5.4/lua 别名）
- pcre2/10.45.1（pkg-config 名 libpcre2-8）
- 系统库 libm / libdl / libpthread（内嵌 Lua + dlopen）

> agg **不是**依赖：已核实 lite-xl 2.1.8 `subprojects/` 只有 freetype2.wrap/lua.wrap/pcre2.wrap，
> 无 agg.wrap、无 agg 引用（旧配方中 agg 假设已移除）。

## OHOS 适配要点

- Meson + PkgConfigDeps：依赖全走 conan，`wrap_mode=nodownload` 禁止 meson 网络下载子项目
- Lua 使用系统包：`use_system_lua=true`，避免下载 lua.wrap（与 nodownload 配合）
- OHOS 下 meson 需注入 ar/ranlib 全路径到 `conan_meson_native.ini`
- 产物可执行文件需 `binary-sign-tool` 签名（OHOS XPM 要求）
- 详细适配过程见 `2.1.8/notes.md`

## 验证状态

- 2.1.8：W3 `conan create` 已在真实环境通过（2026-08-17，`/data/service/hnp/bin` clang 15.0.4 工具链）——
  主包从源码全量编译（14 目标 + 链接）+ meson install，test_package 实质运行 `bin/lite-xl`
  （SDL dummy + `$LITE_USERDIR/init.lua`）输出 `LITE_XL_TEST_OK`、退出码 0。
  W0 依赖发布检查：freetype/lua/pcre2 已在 ohpcd remote 发布；sdl3/3.4.8 本地缓存 recipe+built binary 算就绪。
  状态 `built`（R29：verify 通过未 upload），`.ci-result.json` 由 finish 流程写入（未手动创建）。
