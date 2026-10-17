# DRAFT-appstream-1.2.0-r05-mediaworker-capability-adaptive — mediaworker 按依赖能力上报并自适应初始化/测试格式选择

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-25
> **Severity**: medium (2) | **Category**: capability / init / vips / worker / feature-detect
> **Audience**: mediaworker/IPC 服务消费具备部分能力依赖的库（vips 等）

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R05）：vips/8.18.4.1 制品仓版本仅启用
  PNG/JPEG；媒体 worker 启动时 `asw_image_backend_init` 曾因 JPEG-XL/SVG loader 缺失
  （libjxl/librsvg 真实不可得）硬失败；compose 测试亦无条件断言全部格式。

## 症状（symptom）

```
The libvips library was built without JPEG-XL (libjxl) support
Unable to save JPEG-XL image: VipsOperation: class "jxlsave_target" not found
```

## 机制（root cause）

上游把 PNG/JPEG-XL/SVG 全部当作 backend「absolute requirement」。制品仓 vips 特性矩阵
缺 libjxl/librsvg（libjxl 六包名 + 二进制双查 0 命中，真实外部依赖），硬失败使整个
worker 不可用，即使核心格式 PNG/JPEG 实际可用。

## 修复（fix）

- 0010-asw-image：backend 初始化 PNG/JPEG 硬性、JXL/SVG 降级为 `g_message` 能力警告。
- 0017 asc-media：worker handshake hello 上报 `image-formats`
  （`asw_image_supported_format_names()` 实测集合）；客户端解析并暴露
  `asc_media_supports_image_format()`。
- 0011/0018：compose-worker 与 compose 测试按能力选格式（JXL 缺时回退 PNG，
  与上游 Landlock/libvips-version skip 模式一致）。

## 验证（verification）

- as-test_compose 18/18（MediaImage/MediaFont/…）、as-test_compose-worker 10/12+2 能力跳过；
  新增 harmonyos_compose_test 21 项断言：supports(png)=TRUE、supports(jxl)=FALSE。

## 适用边界 / 反例

- 适用：核心格式可用、可选格式依赖缺失的 worker/IPC；调用方需按能力协商格式；
- 反例：可选格式为业务硬性要求时不得降级（须拒绝并报缺失）。

## 关系

- 查重：E008/E051/其他 vips 条目无关；本候选为依赖能力上报 + 初始化的完整闭环。
- similar_to: []; caused_by: vips 特性矩阵（libjxl/librsvg 不可得）;
  prerequisite_of: []; conflicts_with: []

## 证据

- 补丁：patches/0010-asw-image-optional-codecs.patch、0011-compose-worker-feature-detect.patch、
  0017-asc-media-image-formats.patch、0017b-asc-media-h-image-formats.patch、
  0018-test-compose-font-format.patch
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 18