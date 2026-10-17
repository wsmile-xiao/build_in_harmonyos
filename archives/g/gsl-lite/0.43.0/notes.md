# gsl-lite 0.43.0 适配笔记（bootstrap 阶段）

## 源码核验（bootstrap 证据）

- 官方仓库: https://github.com/gsl-lite/gsl-lite
- 正式标签: v0.43.0
- 标签 commit: ce82d30be6f76a38d90605694f0c8fa201723baf
  - commit message: "Prepare for v0.43.0 release"
  - committer date: 2025-05-04T22:56:47Z
- 官方 tarball URL: https://github.com/gsl-lite/gsl-lite/archive/refs/tags/v0.43.0.tar.gz
  - 实际下载经 codeload.github.com/gsl-lite/gsl-lite/tar.gz/refs/tags/v0.43.0
- sha256: e48c3138648156d2b85905b1d280d661fad61524c5c0ca10d3857036ca3dd519
- 单头文件存在: include/gsl-lite/gsl-lite.hpp
- 核验方式: GitHub API git/refs/tags/v0.43.0 + commits/v0.43.0（标签直接指向 commit，非 annotated tag）

## 依赖

header-only 库，无外部依赖。

## 平台注意

- header-only，无需 ELF 签名 / RPATH
- CMake 需处理 OHOS 平台识别（E092: CMAKE_SYSTEM_NAME 映射为 Linux）
---

**编译结束**: 2026-08-31 19:16
**最终状态**: built
