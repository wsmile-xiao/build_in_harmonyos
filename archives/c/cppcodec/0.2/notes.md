# cppcodec 0.2 — 适配笔记

## 来源核验（Bootstrap R01, 2026-08-29）

- 官方仓库: https://github.com/tplgy/cppcodec
- 官方 tag: v0.2 -> commit `302dc28f8fd5c8bf2ea8d7212aed3be884d5d166` (2018-08-20)
- tag 为 GitHub 已验证签名（GPG verified，key 4AEE18F83AFDEB23 已过期属正常历史状态）
- 官方源码 tarball:
  `https://github.com/tplgy/cppcodec/archive/refs/tags/v0.2.tar.gz`
- SHA-256: `0edaea2a9d9709d456aa99a1c3e17812ed130f9ef2b5c2d152c230a5cbc5c482`
- License: MIT

## 库特性

- 纯 header-only C++11 库：base64 / base64url / base32 / base32hex / hex 编解码。
- 头文件树 `cppcodec/`（含 `data/` 与 `detail/` 子目录），无编译产物。
- 上游 CMake 仅构建 test/（Catch2）与 tool/（base64enc/dec 等命令行工具）。
- 上游 CMakeLists.txt 中 `PROJECT_VERSION` 仍是 0.1（tag v0.2 未同步更新），
  版本号以官方 tag v0.2 为准。

## 适配方案

- 按 header-only 库归档，`package_type = header-library`。
- 配方 `package()` 复制 `cppcodec/` 头文件树到 `include/cppcodec/`。
- `test_package/` 编写下游消费者测试（调用 base64/base32/hex API 往返验证）。
- 上游测试（Catch2）在本地验证阶段编译运行；因 tarball 内 `test/catch`
  为空的 git submodule，本地验证时需提供 Catch2 single_include。

## 待办（后续阶段）

- W3 / conan create 本地 CI 验证（G2）
- conan-verify 8 道门禁
- finish 收尾
- submit / PR / 远端 CI
---

**编译结束**: 2026-08-30 08:03
**最终状态**: built
