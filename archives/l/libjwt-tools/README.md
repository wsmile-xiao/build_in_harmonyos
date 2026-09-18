# libJWT Tools

## 简介

libjwt-tools 是 [libJWT](https://libjwt.io) 的命令行工具集，取自 libjwt 源码树 `tools/` 子目录：

- `jwt-verify` —— 校验 JWT（支持 alg none / HS256 / RS256 等）
- `jwt-generate` —— 签发 JWT
- `jwk2key` —— JWK → PEM
- `key2jwk` —— PEM → JWK

- 官网/文档：https://libjwt.io
- 源码仓库：https://github.com/benmcollins/libjwt

## OHOS 适配

- 构建系统：cmake
- 编译器：clang 15.0.4
- 包类型：`application`（只交付 `bin/` 与 `share/man/`，不含头文件与库）
- 补丁：1 个（`patches/0001-cmake-fix-codegen-bash-c.patch`，修复上游 CMakeLists codegen 命令引号拆词）
- 同源父包：`libjwt/3.3.3`（本包 `requires` 它，且与它共用同一官方归档与 sha256）

## 依赖

- libjwt/3.3.3（本体，同源子包）
- openssl/3.5.6（**必须显式声明为 direct require**，原因见下）
- jansson/2.15.1.1（经 libjwt 传递可见）

## 构建产物

- `bin/jwt-verify`、`bin/jwt-generate`、`bin/jwk2key`、`bin/key2jwk`
- `share/man/man1/*.1`（4 个 man page）
- `licenses/LICENSE`

4 个可执行文件均为 ELF64 AArch64（`e_machine=183`）且带 `PT_INTERP`，
`DT_NEEDED` 仅 `libjansson.so` + `libc.so`（上游 `jwt_add_tool()` 用 `PRIVATE jwt_static`
静态链接本体，故工具不依赖 `libjwt.so`）。

## OHOS 适配要点

1. **openssl 必须显式声明为本包的 direct require。** 上游 `CMakeLists.txt:71` 用
   `pkg_check_modules(OPENSSL openssl>=3.0.0 REQUIRED)` 无条件求值，因此 `openssl.pc`
   必须在 generators 目录里。仅靠 libjwt 传递拿不到：libjwt 已把 openssl 静态链入
   `libjwt.so`，该 require 传到消费者层是 `run=false/libs=false`，被
   `_skip_binaries()` 标 `skip=True`，而 `PkgConfigDeps` 只遍历
   `dependencies.host`（已过滤 `skip=True`）→ 不产出 `openssl.pc`
   → CMake configure 报 `No package 'openssl' found`。
2. **不使用 ctest 驱动上游测试**：上游 `add_test()` 硬编码解释器 `/bin/bash`，OHOS 只有
   `/bin/sh`；本配方按 `tests/jwt-cli.bats` 的等价语义逐条复现 9 个用例。
3. **串行构建**：OHOS/musl 下 `make` jobserver 并行 spawn 竞态会静默失败，配方用
   `subprocess` 直接 `make -j1` 构建 4 个工具目标。
4. **HarmonyOS SONAME 补偿**：`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` +
   `CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG`（与父包 libjwt 同款三行）。

## 参考

- 适配笔记：`archives/l/libjwt-tools/3.3.3/notes.md`
- 上游测试：9 个 bats 用例（`tests/jwt-cli.bats`），本机实测全部通过
- 消费者测试：37/37（`test_consumer` 12 + `test_ohos` 21 + 工具端到端 4）
