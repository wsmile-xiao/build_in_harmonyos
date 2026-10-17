# secp256k1 0.7.1 适配笔记

## 编译环境

- 构建系统: CMake
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
cmake -S . -B build \
  -DBUILD_SHARED_LIBS=OFF \
  -DSECP256K1_ENABLE_MODULE_ECDH=ON \
  -DSECP256K1_ENABLE_MODULE_SCHNORRSIG=ON \
  -DSECP256K1_ENABLE_MODULE_EXTRAKEYS=ON \
  -DSECP256K1_BUILD_TESTS=OFF
cmake --build build --parallel 1
cmake --install build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Windows本地conan-verify失败 | Windows环境缺少OHOS交叉编译工具链（clang/make等） | 配方已在CI环境验证，本地仅做配方完整性检查 |
| 2 | E007风险：config.guess不识OHOS | Autotools 的 config.guess/config.sub 可能不识别 OHOS | 改用 CMakeToolchain，避免依赖 config.guess/config.sub |
| 3 | configure 不存在且 autoreconf 失败 | GitHub tag 归档无 configure，CI 缺少 Automake 的 aclocal | 改用上游正式支持的 CMake 构建系统 |

## 源码修改

无

## 依赖版本

无外部依赖（内置 bignum 实现）

## 验证结果

```bash
# 验证静态库存在
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/lib/libsecp256k1.a
# 验证头文件存在
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/include/secp256k1.h
```

## 注意事项

- 使用 BUILD_SHARED_LIBS=OFF 强制静态编译，避免系统同名库污染
- 启用 ECDH、Schnorr 签名和扩展密钥模块以提供完整功能
- 无需外部依赖，内置 bignum 实现确保编译独立性
---

**编译结束**: 2026-07-15 11:29
**最终状态**: built
