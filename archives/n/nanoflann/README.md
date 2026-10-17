# nanoflann

C++ header-only library for KD-tree / KNN search — 轻量 KD 树与最近邻搜索库
（FLANN 的另一独立头文件实现，C++11 起可用）。

- 官方仓库: https://github.com/jlblancoc/nanoflann
- 许可: BSD-3-Clause
- 形态: 单头文件 `include/nanoflann.hpp` + CMake package config（无二进制）

## 版本

| 版本 | 状态 | 构建日期 | 备注 |
|------|------|----------|------|
| 1.7.1 | built | 2026-08-31 | bootstrap 阶段骨架；conan-verify 在首轮 adapt 中执行 |

## 说明

- 适配要点见 `manifest.yaml` 与 `1.7.1/notes.md`。