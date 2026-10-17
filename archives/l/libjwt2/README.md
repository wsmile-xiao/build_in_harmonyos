# libJWT 2.x

JSON Web Token C 库（legacy v2 分支，2.1.3）。

## 功能概述

- JWT 编码/解码（HS256/RS256/ES256 等）
- JWK/JWKS 支持
- OpenSSL 后端加密
- Jansson JSON 后端

## OHOS 适配

- 构建系统：CMake（>=3.7）
- 编译器：clang 15
- Jansson 通过上游 FetchContent（`USE_INSTALLED_JANSSON=OFF`）内嵌，避免对制品仓 jansson 配方的依赖
- OpenSSL 来自 Conan 制品仓 `openssl/3.5.6.1`
- 上游测试（8 个 Check 单测）通过 `BUILD_TESTS=ON` 在 conanfile build() 中以 ctest 真实执行
- 与 `libjwt/3.x` 并存：包名 `libjwt2`，库文件仍为 `libjwt`（上游 `add_library(jwt)`），Conan cmake 目标为 `libjwt2::jwt`

## 依赖关系

- 编译依赖：openssl/3.5.6.1
- 测试依赖：check/0.15.2（上游 8 个单测）
- Jansson：FetchContent v2.14（上游内嵌，不走 Conan）

## 参考资料

- 官网：https://github.com/benmcollins/libjwt
- Release：https://github.com/benmcollins/libjwt/releases/tag/v2.1.3
