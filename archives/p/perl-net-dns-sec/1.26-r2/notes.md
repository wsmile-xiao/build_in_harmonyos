# perl-net-dns-sec 1.26-r2 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL + XS)
- 编译日期: 2026-06-25
- 编译器: clang 18.1.8 (CC=clang, AR=llvm-ar)
- 状态: built (编译成功，运行时XS加载受限)

## 编译步骤

1. 下载源码: Net-DNS-SEC-1.26.tar.gz (CPAN, NLNETLABS)
2. `perl Makefile.PL PREFIX=$DEFAULT_PREFIX`
3. 修改 Makefile:
   - CCFLAGS 添加 `-isystem <sysroot>/include` (解决 sys/types.h 找不到)
   - LDDLFLAGS 改为 `-shared -nostartfiles -nodefaultlibs -lc -O2 -fstack-protector-strong` (CRT workaround)
4. `make -j1`
5. `make install DESTDIR=$TEST_PREFIX`
6. `make test`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sys/types.h` not found | clang 18 无 sysroot，系统头文件不在默认搜索路径 | CCFLAGS 添加 `-isystem /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include` |
| 2 | `endian.h` not found | 同上，_sysheaders_backup 不完整 | 同上方案（使用完整 sysroot include 路径） |
| 3 | XS .so 链接缺少 CRT 文件 | OpenHarmony 缺 crti.o/crtn.o | LDDLFLAGS 添加 `-nostartfiles -nodefaultlibs -lc` |
| 4 | XS .so 运行时加载 Permission denied | SELinux/HMDFS 限制 (hmdfs:s0 类型) | 已知平台限制，**核心加密功能不可用**（见功能测试） |

## 源码修改

无源码修改。Makefile 在生成后手动修改（非 .patch 补丁，编译时通过 conanfile.py 自动应用）。

## 依赖版本

- Perl: 5.42.2
- Net::DNS: 1.55 (满足 >= 1.08)
- OpenSSL: 1.1.1w (libcrypto)
- clang: 18.1.8
- llvm-ar: LLVM

## 验证结果

```
make test 结果:
- t/00-install.t: ok (36 subtests 全部通过)
- t/00-load.t: FAILED ("XS component SEC.xs loaded" 失败 → BAILOUT: "Unable to access OpenSSL libcrypto library")
- t/00-pod.t: SKIP (缺少 Test::Pod 1.45)
- 其他测试: 因 00-load.t bailout 未执行

SEC.so 动态依赖:
- libc.so
- libcrypto.so.1.1
```

## 功能测试 (2026-06-26)

**测试结论**: ❌ **不可正常使用** — 核心 DNSSEC 加密功能不可用

### XS .so dlopen 测试

在 6 个不同路径（/storage/Users/...、/data/local/tmp/、/tmp/、/data/service/hnp/...）测试 dlopen，
全部失败：用户可写路径返回 Permission denied (SELinux)，只读路径返回 No such file or directory。
**OpenHarmony 上所有用户可写路径均被 SELinux 阻止 dlopen。**

### 模块加载测试

| 模块 | 结果 | 说明 |
|------|------|------|
| Net::DNS::SEC (主模块) | ✅ PASS | 纯 Perl 回退，version 1.26 |
| Net::DNS::SEC::Keyset | ✅ PASS | 纯 Perl，无 XS 依赖 |
| Net::DNS::SEC::Private | ✅ PASS | 纯 Perl，无 XS 依赖 |
| Net::DNS::SEC::RSA | ❌ FAIL | `BEGIN { die }` 要求 XS libcrypto |
| Net::DNS::SEC::ECDSA | ❌ FAIL | `BEGIN { die }` 要求 XS libcrypto |
| Net::DNS::SEC::DSA | ❌ FAIL | `BEGIN { die }` 要求 XS libcrypto |
| Net::DNS::SEC::EdDSA | ❌ FAIL | `BEGIN { die }` 要求 XS libcrypto |
| Net::DNS::SEC::Digest | ❌ FAIL | `BEGIN { die }` 要求 XS libcrypto |

### 可用功能 (纯 Perl)

- ✅ 模块加载 (`use Net::DNS::SEC`)
- ✅ 算法编号↔助记符转换 (`algorithm()`)
- ✅ 摘要类型编号↔助记符转换 (`digtype()`)
- ✅ DS 记录创建与解析
- ✅ DNSKEY 记录创建与解析
- ✅ Keyset 文件处理
- ✅ 私钥文件读取 (`Net::DNS::SEC::Private`)

### 不可用功能 (依赖 XS libcrypto)

- ❌ RSA 签名生成与验证 (算法 1/5/7/8/10)
- ❌ ECDSA 签名生成与验证 (算法 13/14)
- ❌ DSA 签名生成与验证 (算法 3/6)
- ❌ EdDSA 签名生成与验证 (算法 15/16)
- ❌ DNSSEC 摘要计算 (`Net::DNS::SEC::Digest`)
- ❌ RRSIG 记录处理 ("type RRSIG not implemented")

### 根因

加密子模块 (RSA/ECDSA/DSA/EdDSA/Digest) 在 `BEGIN` 块中检查
`Net::DNS::SEC::libcrypto->can('EVP_PKEY_new_XXX')`，XS 不可用时直接 `die`。
**模块设计上没有纯 Perl 加密回退实现**，仅主模块和工具函数有纯 Perl 回退。

完整测试报告: `reports/functional-test-report.md`

## 交付物

| 文件 | 说明 |
|------|------|
| SEC.so | XS 共享库 (auto/Net/DNS/SEC/SEC.so) |
| SEC.pm | 主模块 (Net/DNS/SEC.pm) |
| DSA.pm, RSA.pm, ECDSA.pm, EdDSA.pm | 签名算法模块 |
| Digest.pm | 摘要模块 |
| Keyset.pm, Private.pm | 辅助模块 |

## 注意事项

- XS .so 编译链接成功，但运行时因 SELinux/HMDFS 限制无法 dlopen 加载
- **核心加密功能不可用**: RSA/ECDSA/DSA/EdDSA/Digest 子模块均要求 XS libcrypto，无纯 Perl 回退
- 纯 Perl 回退仅限主模块加载和工具函数（algorithm/digtype/DS/DNSKEY/Keyset/Private）
- RRSIG 记录处理不可用（"type RRSIG not implemented"）
- conanfile.py 中通过 regex 自动应用 Makefile 修改（sysroot include + CRT workaround）
- 加密依赖: OpenSSL 1.1.1w (已安装，pkg-config 可发现 libcrypto)
- 软件在鸿蒙平台上**不可正常使用**，仅可作为依赖占位（模块加载层面兼容）
---

**编译结束**: 2026-06-25 16:00
**功能测试**: 2026-06-26
**最终状态**: built (编译成功，功能测试不通过 — 加密功能不可用)
