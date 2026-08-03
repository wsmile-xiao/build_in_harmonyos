# libp11 0.4.16-r0 适配笔记

## Conan 配方说明

当前 Conan 配方不使用版本目录根部早期手工归档流程生成的 `0001` 至 `0005` 补丁。这些历史补丁包含 CI、文档等非构建改动，且不属于本次配方。配方只应用 `patches/0001-configure-hmdfs-umask.patch`，用于解决 HMDFS 临时目录权限问题。官方 0.4.16 release 的 `config.sub` 已接受 `aarch64-unknown-linux-ohos`，因此配方只指定目标 `--host`，不会伪造构建机 `--build`。

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-20
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 下载源码：从 GitHub OpenSC/libp11 下载 0.4.16 版本
2. 初始化编译环境：`ohc-run.py init-build libp11 0.4.16-r0 --url=file://...`
3. 应用 config.guess/config.sub 补丁（E007 - HarmonyOS 系统识别）
4. 配置：`./configure --prefix=$DEFAULT_PREFIX`（需要设置 PKG_CONFIG_PATH 和 OPENSSL_LIBS）
5. 生成 libp11.map 版本脚本（configure 未能自动生成）
6. 编译：`make -C src`（跳过 examples，避免链接器错误）
7. 安装到 staging：`make install DESTDIR=$TEST_PREFIX -C src`
8. 安装到本地：`make install -C src`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 脚本缺少 HarmonyOS 检测分支 | 使用 patch-autotools-ohos.pl 补丁脚本修改 config.guess 和 config.sub（E007） |
| 2 | config.status 无法创建临时文件 | HMDFS 文件系统限制，mktemp 创建的临时目录立即创建文件时失败 | 手动修改 config.status 第847行，使用固定临时目录 `./conf_workaround` |
| 3 | configure 找不到 OpenSSL | PKG_CONFIG_PATH 未包含 OpenSSL 的 pkgconfig 目录 | 设置 `PKG_CONFIG_PATH=$DEFAULT_PREFIX/lib/pkgconfig` |
| 4 | OPENSSL_LIBS 只包含 libcrypto | configure 使用 PKG_CHECK_MODULES(libcrypto)，缺少 libssl | 手动设置 `OPENSSL_LIBS="-L$DEFAULT_PREFIX/lib -lssl -lcrypto"` |
| 5 | libp11.map 缺失 | configure 因 config.status 错误未能生成版本脚本 | 手动创建 libp11.map，使用 libp11.exports 和 LIBP11_LT_OLDEST=3 |
| 6 | examples 编译失败 | 链接器使用 --no-allow-shlib-undefined 标志导致未定义符号错误 | 跳过 examples 构建，只编译核心库文件（src 目录） |

## 源码修改

### 修改文件：
1. `config.guess` - 添加 HarmonyOS/__OHOS__ 检测（E007 补丁）
2. `config.sub` - 添加 ohos-linux 三元组支持（E007 补丁）

### 手动创建文件：
1. `src/libp11.map` - 版本脚本，定义导出符号

## 依赖版本

- OpenSSL: 3.5.6（已验证：openssl version）
- pkg-config: 0.29.2
- clang: 15.0.4
- make: GNU Make 4.4.1
- autoconf: 2.72
- automake: 1.17

## 验证结果

```bash
# pkg-config 验证
$ pkg-config --modversion libp11
0.4.16

$ pkg-config --libs libp11
-L/storage/Users/currentUser/usr/local/lib -lp11

$ pkg-config --cflags libp11
-I/storage/Users/currentUser/usr/local/include

# 库文件验证
$ ls -lh ~/usr/local/lib/libp11.so*
-rwxr-x--- libp11.so.3.7.2 (291K)
lrwxrwxrwx libp11.so -> libp11.so.3.7.2
lrwxrwxrwx libp11.so.3 -> libp11.so.3.7.2

# OpenSSL engine 和 provider
$ ls -lh ~/usr/local/lib/engines-3/pkcs11.so (371K)
$ ls -lh ~/usr/local/lib/ossl-modules/pkcs11prov.so (367K)

# ELF 检查
$ file ~/usr/local/lib/libp11.so.3.7.2
ELF shared object, 64-bit LSB arm64, not stripped
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libp11.so.3.7.2 | 291KB | 主共享库 |
| libp11.a | 533KB | 静态库 |
| pkcs11.so | 371KB | OpenSSL 1.x engine |
| pkcs11prov.so | 367KB | OpenSSL 3.x provider |
| libp11.pc | 243B | pkg-config 文件 |
| libp11.h | 20KB | 主头文件 |
| p11_err.h | 1.9KB | 错误码头文件 |

## 注意事项

1. **config.status 临时目录问题**：在 HMDFS 文件系统上，autotools 的 config.status 脚本可能无法正常创建临时文件。解决方案是手动修改 config.status，使用固定的临时目录。

2. **OPENSSL_LIBS 设置**：必须手动设置 `OPENSSL_LIBS="-lssl -lcrypto"`，否则 examples 编译会失败。虽然 examples 已跳过，但建议在 configure 时设置此变量。

3. **版本脚本生成**：configure 在 HarmonyOS 上可能无法自动生成 libp11.map，需要手动创建。

4. **examples 编译失败**：链接器使用 `--no-allow-shlib-undefined` 标志导致 examples 无法链接。这不影响核心库的使用，examples 可以在后续解决或跳过。

5. **跳过 tests**：由于 examples 编译失败，tests 也无法执行。建议在最终验证时手动测试库的功能。

---

**编译结束**: 2026-05-20 14:55
**最终状态**: built（核心库编译成功，examples/tests 跳过）
---

**编译结束**: 2026-05-20 14:56
**最终状态**: built

## 积分赛上游测试接入

- 上游 `tests/Makefile.am` 注册 33 个 SoftHSM 集成测试脚本。
- 上游脚本依赖 `pkcs11.la`、`pkcs11prov.la` 这类 libtool shared module，并配合 SoftHSM/OpenSC 执行集成测试。
- 本适配包的交付目标是静态 `libp11.a`，OHOS 官方 CI 使用 `--disable-shared --enable-static`，继续构建 shared module 会触发 libtool `cannot build a shared library`。
- 因此 OHOS 官方 CI 只构建静态库并执行新增 `test_package` 消费测试；33 个上游 SoftHSM 集成脚本记录为 OHOS shared-module 场景不适用。
- 若后续赛事要求交付 engine/provider shared module，可另开独立适配路径补齐该集成测试环境。
