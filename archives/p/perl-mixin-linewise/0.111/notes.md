# perl-mixin-linewise 0.111 适配笔记

## 编译环境
- 构建系统: perl (ExtUtils::MakeMaker)
- 编译日期: 2026-06-18
- 编译器: clang/clang++ 18.1.8
- 状态: built

## 编译步骤

```bash
cd ~/tmp/builds/perl-mixin-linewise-0.111.work
perl Makefile.PL
make
make install DESTDIR=~/tmp/test-install-perl-mixin-linewise-0.111
```

纯 Perl 模块，使用标准 `perl Makefile.PL && make && make install` 流程，无需修改源码。

## 依赖处理

### Sub::Exporter（纯 Perl）
- 从 CPAN 下载 Sub-Exporter-0.987.tar.gz
- `perl Makefile.PL && make && make install`（INSTALL_BASE=~/usr/local）
- 安装成功，版本 0.991

### PerlIO::utf8_strict（XS 模块）
- 从 CPAN 下载 PerlIO-utf8_strict-0.010.tar.gz
- 编译需要 musl 头文件和 OHOS SDK sysroot
- 参考 perl-dbd-pg 编译经验处理链接问题

**编译参数**：
```bash
# CFLAGS（编译）
-I~/usr/local/include -D_GNU_SOURCE -fno-strict-aliasing -pipe -fstack-protector-strong

# LDDLFLAGS（链接）- 修改 Makefile
-L$SYSROOT/usr/lib/aarch64-linux-ohos \
-L$LLVM_LIB/aarch64-linux-ohos \
-nodefaultlibs -lunwind -lc
```

**关键变量**：
- SYSROOT=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot
- LLVM_LIB=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib

**签名**：
```bash
/data/service/hnp/bin/binary-sign-tool sign \
  -inFile utf8_strict.so -outFile utf8_strict.so.signed -selfSign 1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make test 3/4 失败 | 缺少 Sub::Exporter 和 PerlIO::utf8_strict | 手动从 CPAN 下载编译安装 |
| 2 | PerlIO::utf8_strict 编译找不到 sys/types.h | 系统缺少 musl 头文件路径 | 添加 `-I~/usr/local/include` 到 CCFLAGS |
| 3 | PerlIO::utf8_strict 链接找不到 libc/libunwind | 链接器默认搜索路径不含 OHOS SDK | 修改 LDDLFLAGS 添加 sysroot 和 LLVM lib 路径 |
| 4 | utf8_strict.so 无法加载 (Permission denied) | SELinux HMDFS 限制 (hmdfs:s0) | 创建 HNP 包，管理员安装到系统目录 |
| 5 | make install 写入 /data/service/hnp 失败 | site_perl 目录权限仅 installs 用户 | 使用 DESTDIR + 本地安装 |

## 源码修改

无。perl-mixin-linewise 是纯 Perl 模块，无需修改源码。

## 依赖版本

| 依赖 | 版本 | 类型 | 状态 |
|------|------|------|------|
| Sub::Exporter | 0.991 | 纯 Perl | ✅ 已安装到 ~/usr/local |
| PerlIO::utf8_strict | 0.010 | XS | ✅ 已编译签名（HNP 包就绪） |
| Carp | 系统内置 | 纯 Perl | ✅ |
| IO::File | 系统内置 | 纯 Perl | ✅ |

## 验证结果

```
Writers 模块加载: PASS (v0.111)
write_string 功能: PASS
write_file 功能: PASS
binmode 选项: PASS
多 writer 导出: PASS
空数据处理: PASS
Readers 模块: PLATFORM_LIMIT (需要 PerlIO::utf8_strict 安装到系统目录)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-mixin-linewise-0.111-ohos-aarch64.tar.gz | 29207B | 预编译包（纯 Perl 模块） |
| PerlIO-utf8_strict-0.010.hnp | 8076B | XS 依赖 HNP 安装包 |

## 注意事项

1. **Readers 模块平台限制**: Mixin::Linewise::Readers 硬依赖 PerlIO::utf8_strict XS 模块。该 XS 模块编译成功但因 SELinux 限制（HMDFS hmdfs:s0 vs hnp_file:s0）无法从 `~/usr/local` 加载。管理员需安装 HNP 包到 `/data/service/hnp/perl.org/perl_5.42.0/`。

2. **Writers 模块完全可用**: 不依赖 XS 模块，纯 Perl 实现，开箱即用。

3. **Makefile.PL 不接受 LDFLAGS 参数**: 需要直接修改生成的 Makefile 中的 LDDLFLAGS 行。perl-dbd-pg 编译经验同样遇到此问题。

4. **测试库设计问题**: `t/lib/MLTests.pm` 同时加载 Readers 和 Writers，即使只测 Writers 也会因 Readers 失败而中断。
---

**编译结束**: 2026-06-18 16:23
**最终状态**: built
