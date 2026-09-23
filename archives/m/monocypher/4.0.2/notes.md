# monocypher 4.0.2 适配笔记

## 编译环境
- 构建系统: makefile（无 configure，纯 Makefile）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 (aarch64)
- 状态: built

## 编译步骤

1. 核验官方版本：GitHub tag `4.0.2` → commit `0d85f98c9d9b0227e42cf795cb527dff372b40a4`。
2. 源码选择：官方 release tarball（`https://github.com/LoupVaillant/Monocypher/releases/download/4.0.2/monocypher-4.0.2.tar.gz`，
   sha256 `38d07179738c0c90677dba3ceb7a7b8496bcfea758ba1a53e803fed30ae0879c`）。
   **注意**：tag 归档（`archive/refs/tags/4.0.2.tar.gz`）与 release 分发物内容不同——release 含
   `tests/vectors.h`（上游测试必需）且 `src/monocypher.{c,h}` 版本字符串为 `4.0.2`；tag 归档为
   `__git__` 占位符且不含测试向量。构建与测试必须使用官方 release 分发物。
3. `make library`：构建 `lib/libmonocypher.a` + `lib/libmonocypher.so.4`（含可选 ed25519 模块）。
4. `make check`：运行上游完整测试套件（39 个测试函数、87 处断言）→ **All tests OK!**
5. `make install DESTDIR=<staging> PREFIX=usr/local`：产物为 include 头、.a/.so、.pc、man 页。
6. 固化为 Conan 配方：`conanfile.py` + `conandata.yml` + `test_package/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 URL 返回 HTML | URL 指向仓库页而非 tarball | 使用官方 release tarball URL |
| 2 | tag 归档 `make check` 无法构建 | tag 归档缺 `tests/vectors.h`（需 libsodium 生成） | 改用官方 release 分发物（自带向量） |
| 3 | autotools 模板不适用 | monocypher 无 configure 脚本，是纯 Makefile 项目 | 用 conanfile-makefile 模板重写配方 |
| 4 | 上游默认 CFLAGS 含 `-march=native` | 上游 makefile 默认值，CI 不可移植 | 配方显式传 `CFLAGS='-O2 -fPIC'` |
| 5 | 上游 4.0 无 crypto_sha512 | 4.0 移除 SHA-512，主哈希为 BLAKE2b | test_package 用 crypto_blake2b 官方向量 |

## 依赖版本

- 无第三方依赖（自包含纯 C 库）。工具链：clang 15.0.4、llvm-ar、GNU Make 4.4.1。

## 验证结果

```bash
# 上游测试
make check
# ... 输出全部测试组 ...
# All tests OK!

# Conan 消费者测试（test_package）
# crypto_blake2b("abc") 官方向量 + crypto_wipe 清零校验 → OK
```

## 注意事项

- 上游 license：BSD-2-Clause OR CC0-1.0（双许可），配方取 BSD-2-Clause。
- 库类型（无 CLI），不需要 commands.json（R38 不适用）。
- 非系统同名库（/lib 下无 libmonocypher），动态/静态均允许；默认 shared=False。
---

**编译结束**: 2026-09-05 22:06
**最终状态**: built
