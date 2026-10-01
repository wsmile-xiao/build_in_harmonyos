# sxmo-st — Sxmo Terminal Emulator

**Package**: sxmo-st
**Version**: 0.8.4.1
**Upstream**: https://git.sr.ht/~mil/sxmo-st
**License**: MIT
**Build System**: POSIX Makefile
**Type**: Application (CLI tool)

## Description

sxmo-st is a fork of the suckless `st` terminal emulator adapted for the SXMO
(Simple X Mobile) Linux mobile environment. It is a lightweight X11 terminal
emulator that uses Xft for font rendering and fontconfig/freetype2 for font
discovery.

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| libx11 | 1.8.13 | X11 client protocol |
| libxft | 2.3.9 | X FreeType font rendering |
| fontconfig | 2.18.3 | Font discovery and matching |
| freetype | 2.14.3 | Font rendering engine |
| xorgproto | 2025.1 | X11 protocol headers (Xatom.h, etc.) |
| libxrender | 0.9.12 | X Render extension |
| pkgconf | 3.0.6 (tool) | pkg-config for build |

## OHOS Adaptation

### Build Patches

- `config.mk` is rewritten to inject conan dependency include/lib paths.
- CC=clang is passed (Makefile defaults to `c99` which doesn't exist on OHOS).
- PKG_CONFIG_PATH is set to find fontconfig/freetype pkg-config files.
- Library linkage includes `-lfontconfig -lfreetype` for symbols used by Xft.h.

### Include Path Complexity

X11 headers are split across packages:
- `libx11` provides `X11/Xlib.h`, `X11/XKBlib.h` in `include/X11/`
- `xorgproto` provides `X11/Xatom.h`, `X11/keysym.h`, `X11/extensions/render.h` in `include/X11/`
- `libxrender` provides `X11/extensions/Xrender.h` in `include/X11/`
- `freetype` provides `ft2build.h` in `include/freetype2/`

### Upstream Tests

Upstream has no automated tests (no test directory, no test targets, no `make check`).

### OHOS Consumer Test

A consumer test (`ohos_x11_consumer.c`) verifies that the X11/Xft/fontconfig
libraries can be consumed by a downstream application. It exercises real
API calls: XInitThreads, FcInitLoadConfigAndFonts, FcFontSetCreate, XftInit.
### 对话 #1 [2026-09-29]

- 问题
  - 上游 tar.gz URL 失效、依赖版本冲突、X11 头文件分散（Xatom.h/Xrender.h/ft2build.h）、CC=c99 不存在、test_package 编译消费者找不到传递依赖头文件、CI 预下载把 conandata.yml 注释中的 URL 当 tarball 下载、W3 L0 门禁 stub_test_method。
- 操作
  - 改用 git.sr.ht 归档 URL；统一 freetype 2.14.3、pkgconf 3.0.6；补 xorgproto/libxrender 依赖；config.mk 重写注入依赖路径 + CC=clang；test_package 声明 xorgproto 直接依赖并手动聚合 cpp_info 路径；删除 conandata.yml 注释 URL；test() 方法用 self.run 实际编译并链接 ohos_x11_consumer.c，静态验证 5 个消费者 API 符号导出；真实执行因 HMDFS FUSE 跨会话 exec ACL（E011 类）被拒，如实记为 sandbox SKIP。
- 结果
  - conan create 成功（G2 通过）；test_package 5 项检查：4 过 1 跳过（消费者真实执行被沙箱 ACL 阻断，compile+link+符号验证通过）；W3 本地 CI 全绿；finish 到达 Step 10 submit 预检，剩余打包与报告项见 test-report.md。
### 对话 #2 [2026-09-29]

- 问题
  - PR #13762 CI（#64539）在 conan-build-test 的 test_package 阶段失败：`Package 'sxmo-st/0.8.4.1@ohpcd/stable' not resolved ... Required by 'sxmo-st-test/None'`（包本体构建与 L0/KC/JC 门禁均通过）。
- 操作
  - 根因：test_package/conanfile.py 使用 Conan 1.x 风格类属性 `name = "sxmo-st-test"` 与 `requires = "sxmo-st/0.8.4.1@ohpcd/stable"`，把被测包硬编码为带 user/channel 引用；CI 以无通道模式（plain name/version）构建，干净缓存中不存在该带通道包。本地此前因缓存残留 sxmo-st/0.8.4.1@ohpcd/stable 而掩盖了该问题。
  - 修复：移除 name/requires 类属性（对齐仓库既有 CLI 包 test_package 标准写法），requirements() 改用 `self.requires(self.tested_reference_str)`。
  - 验证：清空本地 sxmo-st 缓存（含带通道残留）后，以 CI 同款环境复现（CONAN_USER=ohpcd CONAN_CHANNEL=stable，无通道模式）运行 ci/conan/build_and_test.sh。
- 结果
  - conan create 通过，test_package 实际执行（L1a/L1b 通过），Build Summary 1/1 通过，L5 产物检查通过；消费者真实执行仍因 HMDFS FUSE exec ACL（E011 类）跳过，静态符号验证 5/5 通过。
---

**编译结束**: 2026-09-29 14:33
**最终状态**: built
