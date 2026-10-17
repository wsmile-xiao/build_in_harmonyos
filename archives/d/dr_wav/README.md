# dr_wav

> WAV audio loading and writing made easy — single-file C library (public domain or MIT-0).

## 简介

dr_wav 是 David Reid（mackron）dr_libs 家族的单头文件（single-header）WAV 音频
读写库。整个库就是单个 `dr_wav.h`，消费者 `#include "dr_wav/dr_wav.h"` 并在
**恰好一个**翻译单元中定义 `DR_WAV_IMPLEMENTATION` 即可编译进实现，无外部依赖。

- 上游仓库：https://github.com/mackron/dr_libs （dr_wav 以 `wav-<版本>` 标签发布）
- 版本：0.13.17（标签 `wav-0.13.17`）
- License：Unlicense OR MIT-0（任选其一）
- 构建形态：header-only（`package_type = header-library`），不产出 lib/ 制品

## 状态

Bootstrap 阶段：已建立最小归档/配方骨架，源码核验完成（official tag +
SHA-256）。编译验证与发布由后续 Adapt 阶段完成。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.13.17 | bootstrap | 骨架已建，待 adapt |