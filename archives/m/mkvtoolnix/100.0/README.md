# mkvtoolnix

> Matroska 多媒体容器工具集（mkvmerge/mkvinfo/mkvextract/mkvpropedit），打包自官方 Moritz Bunkus 发布源。

## 简介

MKVToolNix 是 Matroska（.mkv）容器的开源工具集，包含 mkvmerge（封装/拆分/合并）、mkvinfo（信息查看）、mkvextract（解封装）与 mkvpropedit（属性编辑）四个命令行工具。本归档基于官方 `release-100.0`（mkvtoolnix-100.0.tar.xz，SHA-256 `74480d07a261beeaa8baf898248e668ecc56335e2527bbffa841ef056dc028a1`），在 HarmonyOS PC（aarch64）上以 CLI 工具方式构建，GUI 按 `--disable-gui` 排除。

## OHOS 适配要点

- 构建系统为 autoconf `./configure` + rake（Ruby），非 make；安装用 `rake install`（支持 DESTDIR）。
- Qt6（qtbase >= 6.2.0）为强制依赖（ac/qt6.m4 缺失即报错），即使 `--disable-gui` 也必需。
- libebml/libmatroska/fmt/pugixml/nlohmann-json/utf8cpp/librmff 使用源码自带 bundled fallback。
- C++20 为硬性要求，recipe 覆盖 CI profile 的 cppstd=17。
- 4 个适配补丁：config.guess HarmonyOS 识别、DocBook XSL 降级跳过 man 页、Rakefile 跳 manpages、configure umask 022（HMDFS）。

## 排除与替代

- `mkvtoolnix-gui`（GUI）未构建：本归档为 CLI 工具包，`--disable-gui` 排除；如需 GUI 请另行适配 Qt Widgets 全量依赖。
- 上游行为测试套件（约 630 用例）不可本地复现：官方样本含版权素材不可分发（README #4）；单元测试 296/296 通过，另含运行时自生成的 Matroska 集成测试作为独立本地覆盖。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| zlib | 1.3.1 | 压缩 |
| libogg | 1.3.6 | Ogg 访问 |
| libvorbis | 1.3.7 | Vorbis |
| gmp | 6.3.0.1 | Boost multi-precision GMP 后端 |
| boost | 1.84.0 | filesystem/system/operators |
| qtbase | 6.11.1 | Qt6 Core（强制，即使无 GUI） |
| libebml | 1.4.5 | bundled（源码内） |
| libmatroska | 1.7.1 | bundled（源码内） |

## 功能验证

```bash
mkvmerge --version
mkvinfo --version
mkvpropedit --version
# 自生成 Matroska 集成测试见 test_package/test.sh（运行时生成 125 字节极简 EBML/Matroska，
# mkvmerge --identify / mkvmerge 生成 / mkvinfo 解析全链路验证）
```

## 参考

- [官方文档](https://mkvtoolnix.download/)
- [源码仓库](https://codeberg.org/mbunkus/mkvtoolnix)
