# infamousPlugins

LV2 音频插件合集（作者 Spencer Jackson / ssj71），共 12 个 DSP 插件：`casynth`、`envfollower`、
`hip2b`、`powerup`、`powercut`、`cheapdist`、`stuck`、`ewham`、`lushlife`、`bentdelay`、`mindi`、`octolo`。

- Homepage: https://github.com/ssj71/infamousPlugins
- License: GPL-2.0-or-later
- Build system: CMake
- Language: C / C++

每个插件按 LV2 bundle 交付：`lib/lv2/<plug>.lv2/<plug>.so` + `manifest.ttl` / `<plug>.ttl`
（上游带预置的还有 `*_presets.ttl`）。LV2 宿主以 `dlopen()` 加载插件，bundle 目录即安装单元。

## 依赖（均已发布到 ohpcd 制品仓）

| 依赖 | 版本 | 被谁使用 |
|------|------|---------|
| `lv2` | 1.18.11-git | 全部插件（header-only：LV2 core + extensions 头） |
| `fftw3f` | 3.3.10 | ewham、lushlife |
| `libzita-resampler` | 1.11.2 | ewham、lushlife |

X11/FLTK 图形界面需要 `cairo` + `ntk`，OHOS 上不存在；上游自带
`if(CAIRO_FOUND AND NTK_FOUND)` 守卫会自动跳过 GUI（DSP 插件不依赖 GUI）。

## OHOS 适配

- **LV2 头布局**：上游使用 2012 年前的 `<lv2.h>` 与 `lv2/lv2plug.in/ns/...` 路径，而 LV2 1.18 只装
  `include/lv2/<spec>/<header>.h`。配方在 `build_folder` 下生成私有兼容头目录并前置 `-I`，
  上游源码零改动。
- **zita-resampler 搜索路径**：上游以裸名 `-lzita-resampler` 链接并 include 其头，由配方注入依赖的
  include/lib 目录。
- **CMake 4 vs `cmake_minimum_required(VERSION 2.8)`** → 命令行 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`。
- **`bin/infamous-rule` 不打包**：独立小工具，主循环永不返回，会挂死平台 smoke test。

## 版本

| 版本 | 状态 | 编译日期 | 产物 |
|------|------|---------|------|
| 0.3.2 | published | 2026-09-24 | 12 个 LV2 bundle（12 个 `.so` + 28 个 `.ttl`） |
