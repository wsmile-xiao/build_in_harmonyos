# astrometry.net 0.98 — Bootstrap 记录

## 基本信息
- 软件: astrometry.net
- 版本: 0.98
- 官方仓库: https://github.com/dstndstn/astrometry.net
- Tag: 0.98
- Commit: 1398028bd039d3c5f66fe5115029f4cb840ce8c1
- 提交日期: 2025-10-30T09:46:14-04:00
- 构建系统: configure + make（自定义 bash 脚本，非 autotools）
- 许可证: GPL-3.0-or-later（BSD-3-Clause for own code, GPL-3.0+ for whole work due to vendored GSL）
- 编译日期: 2026-08-23
- 状态: bootstrap（骨架阶段，未编译）

## 源码校验
- Git archive SHA-256: 78b2b57cc57f69f4d0693c62eb1c5a9edd540250195728cdd90e4a643b5c347f
- GitHub archive tarball SHA-256: fc5c01e41f731a7b59ab9bd05f3c0e29c4539c79e86963e0bd1a05a407088875

## 执行端信息
- executor: pc1-3
- task_id: astrometry.net-0.98-r01-bootstrap-pc1-3-20260823T151500Z
- worktree: /storage/Users/currentUser/junshi_liu/worktrees/pc1-3-astrometry.net-0.98
- 分支: feat/astrometry.net-0.98
- 基提交: 250c1906b6 (!6219 merge feat/tomlplusplus-3.4.0 into main)

## 归档文件清单
- conanfile.py — 最小骨架（autotools 模板）
- conandata.yml — 源码 URL + SHA-256
- manifest.yaml — 版本级元数据
- notes.md — 本文件

## 依赖（待 resolve）
astrometry.net 上游依赖包括：
- libpng (zlib+png)
- libjpeg (jpeglib)
- cfitsio (FITS file I/O)
- gsl (GNU Scientific Library)
- wcslib (WCS coordinate handling)
- libcurl (HTTP/FITS downloads)
以上尚未完成适配发布，需在 adapt 阶段核实。

## 注意事项
- configure 是自定义 bash 脚本，非 autotools autoconf 生成，需手工适配
- 内嵌 GSL 源码，需确认是否剥离使用系统 GSL
- 存在 Python 绑定（需要 numpy），bootstrap 阶段暂不考虑
## R14-R15: libpng 版本冲突与修复

| 项 | 内容 |
|---|------|
| 错误 | `Version conflict: libpng/1.6.39 vs libpng/1.6.58` |
| 根因 | cairo/1.18.4 声明依赖 `libpng/1.6.58`，配方写了 `libpng/1.6.39` |
| 修复 | 改为 `libpng/1.6.58`（与 cairo 一致） |
| 验证 | G1/G2/G3 PASS, finish EXIT=0 |
| 可泛化 | 声明传递依赖时，版本号必须与需求量一致；先查需求方版本约束 |

## 依赖链完整清单

```
astrometry.net 0.98
├── cfitsio/4.6.4
├── gsl/2.8
├── bzip2/1.0.8
├── zlib/1.3.1.1
├── openssl/3.5.6.1
├── cairo/1.18.4
│   ├── libpng/1.6.58
│   └── pixman/0.46.4
└── (libjpeg — optional, not in requirements)
```
# R17: 路径 B 交付完成 - 2026-08-24T07:53:11Z
---

**编译结束**: 2026-08-25 20:57
**最终状态**: built
