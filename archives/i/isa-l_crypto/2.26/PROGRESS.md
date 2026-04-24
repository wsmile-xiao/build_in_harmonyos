# isa-l_crypto 2.26 编译进度

**日期**: 2026-04-24
**状态**: ✅ 编译成功

## 步骤记录

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | URL 搜索，找到 v2.26 tag |
| Step 2 configure | ✅ | 使用 CMake（autotools 缺少 automake）|
| Step 3 make | ✅ | 成功编译 libisal_crypto.so |
| Step 4 install | ✅ | DESTDIR 模式安装成功 |
| Step 5 verify | ✅ | 质量门禁 PASS |
| Step 6 package | ✅ | isa-l_crypto-2.26-ohos-aarch64.tar.gz (304KB) |
| Step 7 local install | ✅ | 本地安装验证成功 |

## 编译细节

### 构建系统选择
- 原计划：autotools（configure.ac 存在）
- 实际使用：CMake（缺少 automake/aclocal）
- CMake 对 aarch64 支持更好

### 配置参数
```bash
cmake .. \
  -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=ON \
  -DBUILD_TESTS=OFF \
  -DBUILD_PERF=OFF \
  -DSAFE_DATA=ON \
  -DSAFE_PARAM=ON
```

### 遇到的问题
1. **缺少 automake**：autogen.sh 失败，切换到 CMake
2. **缺少 OpenSSL 头文件**：部分测试需要 OpenSSL，禁用 BUILD_TESTS 和 BUILD_PERF
3. **aarch64 平台**：使用 base C 实现，无汇编优化（SVE/NEON）

### 编译产物
- libisal_crypto.so (118KB, 共享库)
- 头文件：13 个（md5_mb.h, sha1_mb.h, sha256_mb.h, sha512_mb.h, sm3_mb.h, mh_sha1.h, mh_sha256.h, mh_sha1_murmur3_x64_128.h, rolling_hashx.h, isal_crypto_api.h, types.h, multi_buffer.h, isa-l_crypto.h）
- CMake 配置文件：ISALCryptoConfig.cmake
- pkg-config 文件：libisal_crypto.pc

## 发现与知识

### L2: 构建系统适配
- isa-l_crypto 同时支持 autotools 和 CMake
- CMake 构建对依赖管理更清晰，适合缺少 autotools 工具链的环境
- aarch64 版本使用便携式 C 实现，性能优化有限

### L3: 本版本特定
- v2.26 tag 名称不带 .0 后缀
- OpenSSL 测试依赖可选择性禁用

---

**编译结束**: 2026-04-24 01:28
**最终状态**: partial

---

**编译结束**: 2026-04-24 01:28
**最终状态**: partial
