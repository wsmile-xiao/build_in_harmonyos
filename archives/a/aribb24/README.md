# aribb24

ARIB STD-B24 字幕解码库：JIS 8bit 字符解码与 MPEG-TS caption 流解析。FFmpeg（libaribb24 封装）与 VLC 均使用该库解码日本数字电视字幕（ARIB STD-B24 标准）。

## 功能概述

- ARIB STD-B24 JIS 8bit 字符代码解码（`arib_decode_buffer`）
- MPEG-TS caption 数据流解析（`arib_parse_pes` / `arib_parser_get_data`）
- A/P 两种 profile 解码器初始化
- DRCS 位图、字幕区域（regions）获取

## OHOS 适配

- 构建系统为 autotools；源码包无预生成 configure，构建时自动 autoreconf
- 已移除 `AC_PROG_CC_STDC`（autoconf >= 2.70 中删除）与可选 libpng 的 pkg-config 检查
- 原生构建显式指定 `--build/--host=aarch64-unknown-linux-gnu`
- 上游无自动化测试套件，由 test_package 提供消费者视角的真实解码管线验证

## 依赖关系

- 编译依赖：无第三方依赖（libpng 可选功能未启用）
- 运行依赖：libm

## 参考资料

- 上游仓库：https://code.videolan.org/jeeb/aribb24/
- 原始作者仓库：https://github.com/nkoriyama/aribb24
- 许可证：LGPL-3.0-or-later
