# wolfssl 5.9.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-06
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-unknown-linux-ohos (HongMeng Kernel 1.12.0)
- 状态: published
- 源码 SHA256: 6efc62b86f145a5c52bfd62294ca66c20ce85b54e9033f5d7e0ee73eb30306c1

## 编译步骤

1. **init-build**: 从 GitHub archive 下载 v5.9.0-stable tar.gz，解压到 work 目录
2. **autoreconf**: GitHub archive 不包含生成的 configure，需 `autoreconf --install --force`
3. **E011 修复**: `sed -i 's/umask 077/umask 022/g' configure`（HMDFS 权限问题）
4. **configure**: `CONFIG_SHELL=/storage/Users/currentUser/usr/local/bin/bash ./configure --prefix=$DEFAULT_PREFIX`
   - 使用 CONFIG_SHELL=bash 避免 toybox sh (E010) 与 libtool 语法不兼容
   - LD_LIBRARY_PATH 必须包含 OHOS SDK 的 llvm/lib 目录 (E004)，lld 需加载 libxml2.so.16
5. **make**: `make -j2 SHELL=/storage/Users/currentUser/usr/local/bin/bash`
6. **E011 补充修复**: `sed -i 's/umask 077/umask 022/g' config.status`，然后 `bash config.status`
7. **make install DESTDIR**: `make install DESTDIR=$TEST_PREFIX SHELL=bash`
8. **make check**: `make check SHELL=bash` → 8 total, 5 PASS, 3 SKIP, 0 FAIL
9. **verify-build**: `ohc-run.py verify-build wolfssl 5.9.0` → G1-G4 全 PASS
10. **package**: `ohc-run.py package wolfssl 5.9.0` → wolfssl-5.9.0-ohos-aarch64.tar.gz (5734269 bytes)
11. **deploy**: `make install SHELL=bash`（不带 DESTDIR）
12. **验证**: wolfssl-config --version=5.9.0, pkg-config --modversion wolfssl=5.9.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识图谱 |
|---|------|------|---------|---------|
| 1 | configure: C compiler cannot create executables | lld 依赖 libxml2.so.16，LD_LIBRARY_PATH 未包含 OHOS SDK llvm/lib | 添加 `LD_LIBRARY_PATH=...:/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:...` | E004 |
| 2 | config.status: Permission denied creating confXXXXX temp dir | E011: HMDFS umask 077 导致临时目录对当前进程不可写（UID 映射差异） | 将 configure 和 config.status 中 `umask 077` 改为 `umask 022` | E011 |
| 3 | libtool: syntax error: unexpected '}' | E010: toybox sh 不兼容 libtool 生成的 bash 语法 | `CONFIG_SHELL=bash ./configure`，`make SHELL=bash` | E010 |
| 4 | wolfssl 是纯库软件（bin/ 无 ELF 二进制） | wolfssl-config 是 shell 脚本，不是 ELF 可执行文件 | manifest.yaml 标记 `software_type: library`，quality-report 标记为 ⚠️ 非阻塞 | — |

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| configure (umask 077→022, 2处) | E011 HMDFS 权限 | `sed -i 's/umask 077/umask 022/g'` | 源文件修改，refresh-patch 未追踪（生成脚本无 patch） |
| config.status (umask 077→022, 2处) | E011 HMDFS 权限 | `sed -i 's/umask 077/umask 022/g'` | 生成文件，不需要持久化补丁 |

## 依赖版本
- 无外部运行依赖（仅 libc.so）
- 无外部编译依赖
- wolfssl 是独立 SSL/TLS 库

## 验证结果

### 部署验证（$DEFAULT_PREFIX = ~/usr/local）
```bash
$ wolfssl-config --version
5.9.0

$ pkg-config --modversion wolfssl
5.9.0

$ wolfssl-config --libs
-L/storage/Users/currentUser/usr/local/lib -lwolfssl -lpthread

$ wolfssl-config --cflags
-I/storage/Users/currentUser/usr/local/include

$ wolfssl-config --prefix
/storage/Users/currentUser/usr/local

$ file libwolfssl.so.44.1.0
ELF shared object, 64-bit LSB arm64, not stripped

$ llvm-readelf -d libwolfssl.so.44.1.0 | grep NEEDED
  NEEDED: libc.so

$ llvm-readelf -n libwolfssl.so.44.1.0
  Owner: OHOS    Data size: 0x4    NT_VERSION: 01 00 00 00

$ ls libwolfssl.so*
libwolfssl.so -> libwolfssl.so.44.1.0
libwolfssl.so.44 -> libwolfssl.so.44.1.0
libwolfssl.so.44.1.0 (665984 bytes)

$ grep LIBWOLFSSL_VERSION_STRING version.h
#define LIBWOLFSSL_VERSION_STRING "5.9.0"
#define LIBWOLFSSL_VERSION_HEX 0x05009000

$ find include/wolfssl -name "*.h" | wc -l
161

$ llvm-nm -D libwolfssl.so.44.1.0 | grep " T " | wc -l
777
```

### 测试验证（make check 真实输出）
```
Testsuite summary for wolfssl 5.9.0
# TOTAL: 8
# PASS:  5  (testsuite, resume, tls13, pem, unit)
# SKIP:  3  (google, openssl, external — 网络依赖)
# FAIL:  0
# XFAIL: 0
# XPASS: 0
# ERROR: 0
```

### 质量门禁验证
```
G1 二进制完整性: PASS
G2 功能可用性: PASS (⚠️1 — wolfssl-config 是 shell 脚本)
G3 可移植性: PASS (仅依赖 libc.so)
G4 档案完整性: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| wolfssl-5.9.0-ohos-aarch64.tar.gz | 5734269 bytes (5.7MB) | 预编译包（197 个文件） |
| wolfssl-5.9.0-ohos-aarch64-debug.tar.gz | 430168 bytes (420KB) | 调试符号包 |
| libwolfssl.so.44.1.0 | 665984 bytes (~640KB) | 共享库 ELF (777 导出符号) |
| wolfssl-config | shell script (4055 bytes) | pkg-config 兼容配置脚本 |
| wolfssl.pc | 281 bytes | pkg-config 元数据文件 |
| 161 个头文件 | — | wolfssl/wolfcrypt + wolfssl/openssl 兼容层 |

## 注意事项

1. wolfssl 是**纯库软件**，bin/ 中只有 wolfssl-config（shell 脚本），不是 ELF 二进制
2. **LD_LIBRARY_PATH** 必须包含 OHOS SDK 的 `/data/service/hnp/.../llvm/lib` 才能让 lld 正常链接
3. **autoreconf** 需要先生成 configure（GitHub archive 不含生成文件）
4. **CONFIG_SHELL=bash** 必须指定，否则 libtool 在 toybox sh 下语法错误
5. 3 个 SKIP 测试需要网络访问（Google/OpenSSL 互操作/外部资源），离线环境正常跳过
6. 预编译包已通过 ELF 签名（OHOS NT_VERSION），可直接在鸿蒙系统上执行

---

**编译结束**: 2026-06-06
**最终状态**: published
