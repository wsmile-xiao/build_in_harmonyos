# mkvtoolnix 100.0 — OHOS 适配笔记（R06 首轮）

## 上游身份（已核验）
- 归档：https://mkvtoolnix.download/sources/mkvtoolnix-100.0.tar.xz（11147288 字节，application/x-xz）
- SHA-256：74480d07a261beeaa8baf898248e668ecc56335e2527bbffa841ef056dc028a1（官方 .sha256 一致）
- 标签：codeberg mbunkus/mkvtoolnix release-100.0（HTTP 200）
- 版本：configure.ac `AC_INIT([MKVToolNix],[100.0])`；NEWS.md `Version 100.0 "Do Hot Girls Like Chords" 2026-07-05`

## 构建系统（与常规 autotools 不同）
- `./configure`（autoconf，AC_CONFIG_FILES([build-config])）→ 生成 build-config
- `rake`（或 drake）编译；`rake install` 安装（INSTALL 文档 1-4 步）
- rake installer 支持 DESTDIR（rake.d/helpers.rb: install_dir 使用 c(:DESTDIR)）

## 依赖（R05 dependency_complete + R06 ohpcd 发布核验）
强制（已发布 ohpcd，conanfile requires）：
- zlib/1.3.1 ✅、libogg/1.3.5 ✅、libvorbis/1.3.7 ✅、boost/1.84.0 ✅（>=1.74）
- qtbase/6.11.1 ✅（Qt6 >= 6.2.0，ac/qt6.m4 缺失即报错；即使 --disable-gui 也必需）

bundled fallback（不 requires，configure 自动回退源码内置版本）：
- libebml >= 1.4.4（仓库 1.4.5 未发布 ohpcd，用 bundled）、libmatroska >= 1.7.1（同）、
  fmt >= 8.0.0、pugixml、nlohmann-json、utf8-cpp、librmff

可选（首轮不启用）：flac、cmark（GUI）、libdvdread、gtest（单元测试）、po4a

## 关键适配点（待 runner 实测确认）
1. C++20 硬性要求 → conanfile configure() 覆盖 cppstd=20（CI profile 默认 17）
2. Qt6 定位：configure 需 qmake6（PATH 或 --with-qmake6=<qtbase>/bin/qmake6）
3. CONFIG_SHELL=/data/service/hnp/bin/bash（OHOS 无 /bin/sh）
4. rake 需 ruby（ruby 3.4.5 / rake 13.2.1 已可用）
5. 产物为 CLI 可执行文件（mkvmerge 等）→ commands.json（R38，软件级已建）

## 测试入口（本轮未执行）
- 单元测试：tests/unit（googletest，`rake tests:run_unit`，需 lib/gtest 符号链接）
- 行为套件：tests/test-*.rb（`tests/run.rb`，约 630 个条目；样本含版权素材，仅 CI 可完整运行）
---

**编译结束**: 2026-08-17 09:57
**最终状态**: built
