# libJWT

## 简介

libjwt 是 C 语言实现的 JSON Web Token 库（MPL-2.0），提供 JWS 的生成、签名与校验，
以及 JWK/JWKS 密钥集支持，并附带 4 个命令行工具。

- 官网/文档：https://libjwt.io
- 源码仓库：https://github.com/benmcollins/libjwt

## OHOS 适配

- 构建系统：cmake
- 编译器：clang 15.0.4
- 补丁：1 个（`patches/0001-cmake-fix-codegen-bash-c.patch`，修复上游 CMakeLists codegen 命令引号拆词）

## 依赖

- jansson/2.15.1.1（JSON 后端，REQUIRED）
- openssl/3.5.6（REQUIRED；制品仓仅提供静态库，故静态链入 libjwt.so）
- check/0.15.2（`test_requires`，仅编译期运行上游测试，不向下游传播）

## 构建产物

- `lib/libjwt.so`、`lib/libjwt.a`
- `bin/jwt-verify`、`bin/jwt-generate`、`bin/jwk2key`、`bin/key2jwk`
- `include/jwt.h`、`include/jwt_export.h`

## OHOS 适配要点

1. 上游用 `pkg_check_modules()`（pkg-config）而非 `find_package()` 定位依赖，
   配方必须启用 `PkgConfigDeps` 生成依赖的 `.pc` 文件。
2. libcheck 选择临时目录的优先级为 `TEMP` → `P_tmpdir` 宏 → `TMPDIR` → 当前目录；
   OHOS libc 把 `P_tmpdir` 定义为只读的 `/tmp`，因此只设 `TMPDIR` 无效，必须设 `TEMP`。
3. 上游 `add_test()` 硬编码解释器 `/bin/bash`（OHOS 只有 `/bin/sh`），
   故不使用 ctest，改按 `add_test()` 的等价语义直接执行测试二进制。

## 参考

- 适配笔记：`archives/l/libjwt/3.3.3/notes.md`
- 上游测试：11 个 libcheck 套件 / 147 个用例，本机实测全部通过
