# DRAFT-appstream-1.2.0-r05-dep-feature-version-upgrade — 依赖能力缺口 → 查制品仓同源增强小版本并升级配方

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-25
> **Severity**: medium (2) | **Category**: conan / dependency / version-upgrade / feature-matrix
> **Audience**: Conan 配方消费依赖能力（codec/loader/feature）的库

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R05）：配方声明 vips/8.18.4（R03 交付，
  `_disabled_optional_features` 全禁用），mediaworker 无 PNG loader，MediaImage 失败。

## 症状（symptom）

```
The libvips library was built without PNG support.
```

## 机制（root cause）

依赖小版本在制品仓是能力受限构建；制品仓已发布同源增强版本（vips/8.18.4.1：
启用 PNG/JPEG，libjpeg-turbo/3.2.0 + libpng/1.6.58 + zlib/1.3.1.1）。旧版本声明
无法满足下游硬性能力要求——不是"外部依赖缺失"，而是"版本未跟上制品仓"。

## 修复（fix）

`conanfile.py`：`self.requires("vips/8.18.4")` → `self.requires("vips/8.18.4.1")`。
先 `conan list "vips/*" -r=ohpcd` 查版本，再 `conan download vips/8.18.4.1 -r=ohpcd`
（R35：不用 conan list 判二进制）确认制品可用，升级后重配构建复验。

## 验证（verification）

- vips/8.18.4.1 存在且图像特性启用（配方原文核实）；
- MediaImage 真实 PNG 处理通过；上游 14/14；harmonyos_compose_test supports(png)=TRUE。

## 适用边界 / 反例

- 适用：依赖能力缺口且制品仓有同源增强版本（含特性差异的小版本）；
- 反例：制品仓确无任何可用版本/特性 → 按 R41 外部依赖阻塞止损，保留恢复条件。

## 关系

- 与 R37（同上游版本适配修复后缀 X.Y.Z.N 惯例）互补；本候选是"回查并采用
  制品仓已发布的能力增强版本"的可复用步骤。
- similar_to: R37; caused_by: []; prerequisite_of: DRAFT-appstream-1.2.0-r05-mediaworker-capability-adaptive;
  conflicts_with: []

## 证据

- 配方：archives/a/appstream/1.2.0/conanfile.py（vips/8.18.4.1 require）
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 19