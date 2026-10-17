# libJWT3

## 简介

libjwt3 是 C 语言实现的 JSON Web Token (JWT) 库 v3 系列的 OHOS 适配包，提供 JWS 的
生成、签名与校验，以及 JWK/JWKS 密钥集支持，并附带 4 个命令行工具。上游为
MPL-2.0 许可。

- 官网/文档：https://libjwt.io
- 源码仓库：https://github.com/benmcollins/libjwt

## 功能概述

- JWS 签发与校验：HMAC（HS256/384/512）、RSA（RS/PS 系列）、ECDSA（ES256/384/512）、
  EdDSA（Ed25519/Ed448）
- JWT builder / checker 两段式 API：构造 header/claim、设置校验策略与回调
- JWK / JWKS：密钥集载入、JWK 提取、非法密钥集的错误处理
- 自带 4 个命令行工具：`jwt-verify`、`jwt-generate`、`jwk2key`、`key2jwk`

> 与 `libjwt`（同源 v3.3.3）、`libjwt-tools`（同源 v3.3.3，仅工具）、`libjwt2`（2.x 线）
> 并存，Conan 包名不同、互不冲突。

## OHOS 适配

- 构建系统：cmake（上游 `cmake_minimum_required 3.7...3.15`）
- 编译器：clang 15（`/data/service/hnp/bin/clang`），libc++
- 补丁：1 个（`patches/0001-cmake-fix-codegen-bash-c.patch`，修复上游 CMakeLists
  codegen 命令的引号拆词导致 clang 预处理静默失败）

### 与 Linux 的差异 / 适配要点

1. **依赖定位方式**：上游用 `pkg_check_modules()`（pkg-config）而非 `find_package()`，
   配方必须启用 `PkgConfigDeps` 生成 `jansson.pc`/`openssl.pc`/`check.pc`。
2. **临时目录**：libcheck 选临时目录优先级为 `TEMP` → `P_tmpdir` → `TMPDIR` → 当前目录；
   OHOS libc 把 `P_tmpdir` 定义为只读的 `/tmp`（另有 `/tmp` 只读陷阱，见 E002），
   因此必须把 `TEMP` 指向可写目录，只设 `TMPDIR` 无效。
3. **测试驱动**：上游 `add_test()` 硬编码解释器 `/bin/bash`，OHOS 根文件系统只有 `/bin/sh`
   → 不使用 ctest，按 `add_test()` 的等价语义直接执行测试二进制。
4. **SONAME**：CMake 缺 `Modules/Platform/HarmonyOS.cmake`，
   `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG` 为空（该变量是 `HasSOName()` 的判据），
   须同时设该变量与 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`；
   否则 HMDFS 无法创建版本化符号链接链，链接步骤报 `Permission denied`。
5. **链接形态**：非系统同名库（`/lib`、`/lib64` 下无 `libjwt.so`），按 R26 保持默认动态链接。
6. **构建并行度**：OHOS/musl 下 make jobserver 并行 spawn clang 会静默失败，
   配方改为串行 `make -j1`。

## 依赖关系

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| jansson | 2.15.1.1 | 编译/运行 | JSON 后端（`WITH_JSON_C=OFF`） |
| openssl | 3.5.6 | 编译/运行 | 加密后端；制品仓仅静态库，故静态链入 `libjwt.so` |
| check | 0.15.2 | 仅编译期测试 | `test_requires`，不参与 package_id、不向下游传播 |

## 构建产物

- `lib/libjwt.so`、`lib/libjwt.a`
- `bin/jwt-verify`、`bin/jwt-generate`、`bin/jwk2key`、`bin/key2jwk`
- `include/jwt.h`、`include/jwt_export.h`

## 参考资料

- 适配笔记：`archives/l/libjwt3/3.3.3/notes.md`
- 上游测试：11 个 libcheck 套件（另有 9 例 bats 因镜像无 bats 而上游未注册）
