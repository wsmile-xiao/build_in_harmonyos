# gnuplot 6.0.3.1 — 适配笔记

## 概述
在 Phase 1 (6.0.3 零依赖编译) 基础上，集成 libgd 2.3.3 依赖，使 gnuplot 支持 PNG/JPEG/GIF 图片输出。

## 版本策略 (R37)
同一上游版本 (6.0.3)，修改适配后加后缀 → 6.0.3.1

## 变更内容
1. `conanfile.py`: 添加 `self.requires("gd/2.3.3")`，将 `--without-gd` 改为 `--with-gd`
2. 添加 `AutotoolsDeps` 和 `PkgConfigDeps` 生成器，使 configure 能通过 pkg-config 检测 gd
3. `test_package`: 增加 PNG 图片输出功能测试
4. gd/2.3.3 conanfile.py 修复:
   - 添加 `PkgConfigDeps` 和 `AutotoolsDeps` 生成器（原版缺失，导致 gd 未链接 PNG/JPEG 等）
   - 设置 `--build` 和 `--host` 不同值以进入交叉编译模式
   - 设置 `pkg_config_name='gdlib'` 以匹配 gnuplot configure 的 pkg-config 检测

## 编译验证
- 源码: gnuplot-6.0.3.tar.gz (sha256: ec52e3af8c4083d4538152b3f13db47f6d29929a3f6ecec5365c834e77f251ab)
- 补丁: 0001-configure.patch (umask 077 → 022)
- configure: `--with-readline=builtin --with-gd --without-cairo --without-lua --without-qt`
- 编译成功，configure 确认: `libgd-based png jpeg gif sixel: yes (with animated gif)`

## 图片输出测试
- PNG: 22646 bytes, `PNG image data, 640 x 480, 8-bit/color RGB, non-interlaced` ✅
- JPEG: 44412 bytes, `JPEG image data, baseline, 640x480` ✅
- GIF: 7814 bytes, `GIF image data, version 87a, 640 x 480` ✅

## 已知问题
1. "Cannot open initial state save file: Permission denied" — gnuplot 状态文件权限问题，不影响功能
2. "Fontconfig error: Cannot load default config file" — fontconfig 配置文件未找到，使用内置字体，不影响图片生成
3. WebP 终端未启用（需要 cairo+pango+libwebpmux），但 PNG/JPEG/GIF 均正常工作
---

**编译结束**: 2026-07-23 22:20
**最终状态**: built
