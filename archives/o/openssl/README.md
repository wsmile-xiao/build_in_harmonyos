# OpenSSL for HarmonyOS

## 概述

OpenSSL 在 HarmonyOS/OpenHarmony (aarch64) 上的编译和测试记录。

**可用版本**:
- **4.0.1** (首次适配, OpenSSL 4.x 系列): explicit getrandom entropy, static PIC package, musl-safe fd_set helper, no-pinshared
- **3.5.6.1** (OHOS Conan revision, 推荐): explicit getrandom entropy, static PIC package, and 10/10 HarmonyOS PC target assertions
- **3.5.6** (LTS, 已发布但已取代): RAND consumer may expose the unresolved OHOS `__fd_chk` dependency
- **1.1.1w**: 需自定义平台配置和 `no-asm` 选项

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | OpenSSL |
| 官网 | https://www.openssl.org/ |
| 下载 | GitHub Releases 或 Gitee 镜像 |
| 许可证 | Apache-2.0 (3.x); OpenSSL/SSLeay (1.1.1w) |

## 版本对比

| 版本 | 状态 | 构建系统 | 平台配置 | 汇编优化 | 备注 |
|------|------|----------|----------|----------|------|
| 3.5.6.1 | built | custom-perl | Conan-derived OHOS target/sysroot | disabled | Forced OHOS `conan create` passed; C/CLI target tests 10/10 on HarmonyOS PC |
| 3.5.6 | published | openssl-perl | 内置 linux-aarch64 | 可用 | Superseded on OHOS because a real RAND consumer exposes `__fd_chk` |
| 1.1.1w | published | custom-perl | 需自定义 openharmony-aarch64 | 禁用 (no-asm) | 需补丁支持 |

## OpenSSL 3.5.6.1 OHOS Conan revision

This revision retains the official 3.5.6 source and changes only the OHOS
recipe. It selects `--with-rand-seed=getrandom` so OpenSSL does not compile the
`DEVRANDOM_WAIT`/`FD_SET` path that references the unavailable SDK helper
`__fd_chk`. It also binds the configured SDK target/sysroot, builds upstream
test programs, and uses a real `RAND_bytes` Conan consumer. See E220.
The final CLI reports `/ssl`, `/lib/engines-3`, and `/lib/ossl-modules`
without double-root paths and passes version, SHA-256, and random generation
checks on a HarmonyOS PC target.

## OpenSSL 3.5.6 历史编译记录（已取代）

> 该配置未覆盖真实 RAND consumer 暴露的 OHOS `__fd_chk` 链接问题。
> 新适配和下游依赖应使用 3.5.6.1 配方；以下内容仅保留为历史记录。

### 编译步骤

```bash
# 1. 下载源码（国内镜像）
curl -k -L -o openssl-3.5.6.tar.gz \
  "https://gitee.com/mirrors/openssl/repository/archive/openssl-3.5.6.tar.gz"

# 2. 解压（注意 Gitee 目录名）
tar -xzf openssl-3.5.6.tar.gz
mv openssl-openssl-3.5.6 openssl-3.5.6
cd openssl-3.5.6

# 3. Configure（使用内置 linux-aarch64 target）
perl ./Configure linux-aarch64 \
  --prefix=$HOME/usr/local \
  --openssldir=$HOME/usr/local/etc/ssl

# 4. 编译
make -j$(nproc)

# 5. 安装
make install

# 6. 验证
$HOME/usr/local/bin/openssl version
# 输出: OpenSSL 3.5.6 7 Apr 2026
```

### 关键特性

- **内置平台支持**: OpenSSL 3.x 已内置 `linux-aarch64` target
- **无需补丁**: 直接编译，无需修改源码
- **QUIC 支持**: 3.5.6 支持 QUIC 协议
- **TLS 1.3**: 完整支持 TLS 1.3

### 测试结果

| 测试项 | 结果 |
|--------|------|
| openssl version | ✅ |
| AES 加密解密 | ✅ |
| RSA 密钥生成 | ✅ |
| make test | ⏭️ (跳过，超时) |

## OpenSSL 1.1.1w 编译

### 关键修复

使用 `no-asm` 选项禁用汇编优化，解决了 RSA-PSS 签名验证的 BAD_SIGNATURE bug。

### 编译步骤

```bash
# 1. 解压源码
tar -xzf openssl-1.1.1w.tar.gz
cd openssl-1.1.1w

# 2. 设置环境变量
export TMPDIR=$HOME/tmp
mkdir -p $TMPDIR

# 3. 应用补丁
patch -p1 < patches/0001-Configurations-openharmony-conf.patch
patch -p1 < patches/0002-Configure.patch

# 4. 配置 (关键：使用 no-asm 禁用汇编优化)
./Configure openharmony-aarch64 \
  --prefix=$HOME/usr/local \
  --openssldir=$HOME/usr/local/ssl \
  no-asm

# 5. 编译
make -j$(nproc)

# 6. 安装
make install
```

### 补丁说明

| 补丁文件 | 用途 |
|----------|------|
| `0001-Configurations-openharmony.conf.patch` | 添加 OpenHarmony 平台配置 |
| `0002-Configure.patch` | Configure 自动检测 + shebang 修复 |

### 汇编优化禁用原因

**问题**: ARM64 汇编优化代码在 RSA-PSS 签名验证时有 bug

**错误信息**:
```
error:0407E086:rsa routines:RSA_verify_PKCS1_PSS_mgf1:last octet invalid
error:1417B07B:SSL routines:tls_process_cert_verify:bad signature
```

**解决方案**: 使用 `no-asm` 禁用汇编优化

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| 编译器 | clang (LLVM) |
| 工具链 | llvm-ar, llvm-ranlib, llvm-nm |

## OpenSSL 4.0.1 OHOS Conan 配方

OpenSSL 4.x 系列在 HarmonyOS/OpenHarmony (aarch64) 上的适配。下游如需 OpenSSL 4 的新 API
（ECH、ML-DSA、QUIC 增强、SLH-DSA 等）应引用 `openssl/4.0.1`。

- 构建系统仍是 Perl `Configure`（大写 C），`linux-aarch64` 内置 target
- `--with-rand-seed=getrandom` 显式选择内核熵源，排除 `DEVRANDOM_WAIT`/`FD_SET` 代码路径
- `no-asm`（E006）、`no-shared`、`no-legacy`、`no-module`、`no-docs`、`no-pinshared`、`-fPIC`
- `no-pinshared` 为 4.0 新选项：静态构建默认仍会为 libcrypto/libssl 加 pin 链接标记，
  与 `no-shared` 一起配置以避免第三方共享库被意外 pin
- 4.0 移除 engines（`ENGINESDIR` 不复存在，`no-engine` 恒为禁用态）；`install_sw`
  分解为 `install_dev`/`install_modules`/`install_runtime`
- musl 可移植性补丁两枚（按 4.0.1 上下文重新生成）：`apps/speed.c` 改走
  `openssl_fdset` 有界助手；`include/internal/sockets.h` 在 `__MUSL__` 下用
  `fds_bits` 布局实现该助手（不依赖 SDK 私有 `__fd_chk` 符号）

### 与 openssl 3.x 系列的关系

| 维度 | openssl (3.x) | openssl (4.x) |
|------|---------------|-----------------|
| 包名 | openssl | openssl |
| 版本 | 3.5.x | 4.0.x |
| ENGINESDIR | /lib/engines-3 | （已移除 engines） |
| engine API | 可用（已弃用） | 移除（恒 no-engine） |
| SSLv3/SSLv2 ClientHello | 兼容代码存在 | 移除 |
| ECH (RFC 9849) | 无 | 支持 |
| QUIC | 支持 | 增强（默认启用） |
| 共享库版本 | libssl.so.3 | libssl.so.4（SHLIB_VERSION=4） |

## 经验总结

1. **版本选择**: OHOS 下使用 3.5.6.1 配方；3.5.6 已因 RAND consumer 的 `__fd_chk` 链接缺陷被取代
2. **汇编优化**: 1.1.1w 需禁用汇编优化 (`no-asm`)
3. **Python 链接**: 确保 _ssl.so 正确链接 libssl 和 libcrypto
4. **测试边界**: 交叉构建只证明上游测试程序和真实 consumer 可编译/链接；目标端执行必须在 `can_run=true` 时另行取证
5. **Gitee 镜像**: 国内下载推荐使用 Gitee 镜像

## 参考资料

- OpenSSL 官方文档: https://www.openssl.org/docs/
- OpenSSL Configure 选项: https://wiki.openssl.org/index.php/Compilation_and_Installation
- Gitee 镜像: https://gitee.com/mirrors/openssl
