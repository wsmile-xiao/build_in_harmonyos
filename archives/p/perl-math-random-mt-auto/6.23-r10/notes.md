# perl-math-random-mt-auto 6.23-r10 适配笔记

## 编译环境
- 构建系统: perl_makefile (ExtUtils::MakeMaker)
- 编译日期: 2026-06-17 (修复完善)
- 编译器: clang 18.1.8
- Perl 版本: 5.42.0
- 状态: published

## 编译步骤

1. 下载源码：从 CPAN 下载 Math-Random-MT-Auto-6.23.tar.gz
2. 解压并进入源码目录
3. 修改 Makefile.PL，添加 OpenHarmony SDK sysroot 路径
4. 执行 perl Makefile.PL PREFIX=$DEFAULT_PREFIX
5. 执行 make 编译
6. 安装运行时依赖 Object::InsideOut 3.88
7. make install DESTDIR=$TEST_PREFIX (staging)
8. make install (本地部署)
9. 签名 Auto.so (binary-sign-tool -selfSign)
10. 打包 (ohc-run.py package)
11. 创建 HNP 包 (hnpcli pack)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 状态 |
|---|------|------|----------|------|
| 1 | fatal error: 'sys/types.h' file not found | Perl XS 模块编译时未包含 OpenHarmony SDK sysroot 头文件路径 | 在 Makefile.PL 中添加 INC 参数：`-I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include/aarch64-linux-ohos -I/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot/usr/include` | ✅ 已解决 |
| 2 | ld.lld: error: cannot open crti.o / crtbeginS.o / crtn.o | OpenHarmony musl 不提供标准 CRT 文件 | 在 Makefile.PL 中添加 dynamic_lib OTHERLDFLAGS: `-nostartfiles -nodefaultlibs -lc -L<data>/sysroot/usr/lib/aarch64-linux-ohos` | ✅ 已解决 |
| 3 | 测试失败：Can't locate Object/InsideOut.pm | 缺少运行时依赖 Object::InsideOut 3.88 | 从 CPAN 下载源码手动编译安装（纯 Perl 模块，无 XS 代码） | ✅ 已解决 |
| 4 | XS 模块加载失败：Permission denied | SELinux 限制：HMDFS (hmdfs:s0) 上 dlopen 被拒绝 | 与 perl-dbd-pg 相同的平台限制。创建 HNP 包用于系统级安装到 /data/service/hnp/ (hnp_file:s0) | ⚠️ 需管理员安装 |

## 与 perl-dbd-pg 编译经验对比

| 方面 | perl-dbd-pg | perl-math-random-mt-auto |
|------|-------------|-------------------------|
| 构建系统 | perl_makefile | perl_makefile |
| CRT 缺失 | ✅ `-nostartfiles -nodefaultlibs -lc` | ✅ 相同 |
| sysroot INC | ❌ 不需要（DBI::DBD 提供） | ✅ 需要手动添加 |
| SELinux 限制 | ✅ 遇到 | ✅ 相同 |
| PurePerl 后备 | ✅ DBI::PurePerl | ❌ 无后备实现 |
| HNP 包 | ✅ 已创建 | ✅ 已创建 |
| 处理方式 | 系统级安装 | 相同 |

## 源码修改

- 文件: Makefile.PL
- 补丁: 0001-Makefile.PL.patch
- 内容: 添加 INC 和 dynamic_lib 参数，指向 OpenHarmony SDK sysroot
- 修改类型: 平台适配（非功能修改）
- 守卫: 无需守卫（Makefile.PL 不在运行时执行）

## 编译产物

| 文件 | 大小 | 说明 |
|------|------|------|
| Auto.so | 29,952 bytes | XS 共享库 (ELF64 AArch64, 已签名) |
| Auto.pm | 53,286 bytes | Perl 模块主文件 |
| Range.pm | 10,714 bytes | Range 子模块 |
| tar.gz 包 | 156,715 bytes | 预编译包 |
| HNP 包 | 33,680 bytes | 系统安装包 |

## 依赖版本

- Perl: 5.42.0
- Object::InsideOut: 3.88 (已安装)
- Exception::Class: 1.45 (系统已安装)
- Scalar::Util: 1.23+ (系统已安装)
- clang: 18.1.8

## XS 模块提供的函数

| 包 | 函数 | 返回类型 | 说明 |
|----|------|----------|------|
| Math::Random::MT::Auto | irand() | UV | 32位整数随机数 |
| Math::Random::MT::Auto | rand() | double | [0,1) 浮点随机数 |
| Math::Random::MT::Auto | gaussian() | double | 高斯(正态)分布 |
| Math::Random::MT::Auto | exponential() | double | 指数分布 |
| Math::Random::MT::Auto | erlang() | double | 埃尔朗分布 |
| Math::Random::MT::Auto::_ | seed_prng() | void | 设置随机种子 |
| Math::Random::MT::Auto::_ | set_state() | void | 设置 PRNG 内部状态 |
| Math::Random::MT::Auto::_ | free_prng() | void | 释放 PRNG |

## 验证结果

```bash
# 编译产物检查
file Auto.so
# → ELF shared object, 64-bit LSB arm64

# 签名检查
readelf -S Auto.so | grep codesign
# → .codesign section 存在

# 依赖检查
readelf -d Auto.so | grep NEEDED
# → Shared library: [libc.so]

# Boot 函数检查
readelf --dyn-syms --wide Auto.so | grep boot_
# → boot_Math__Random__MT__Auto

# Perl 语法检查
perl -c Auto.pm
# → syntax OK

# tar.gz 包验证
tar tzf perl-math-random-mt-auto-6.23-r10-ohos-aarch64.tar.gz
# → 21 files
```

## 注意事项

1. Perl XS 模块编译需要添加 OpenHarmony SDK sysroot 的 include 和 lib 路径
2. OpenHarmony musl 不提供标准 CRT 文件，需要使用 `-nostartfiles -nodefaultlibs -lc` 链接参数
3. 本模块依赖 Object::InsideOut（纯 Perl 模块），已手动安装
4. XS 模块 Auto.so 需要安装到 `/data/service/hnp/` 系统目录才能被 Perl DynaLoader 加载
5. 已创建 HNP 包 (`perl-math-random-mt-auto.hnp`) 用于系统级安装
6. 与 perl-dbd-pg 的 SELinux HMDFS 限制是已知平台问题，处理方式一致

## 安装到系统目录（管理员操作）

```bash
# HNP 包方式
unzip ~/tmp/perl-math-random-mt-auto.hnp \
  -d /data/service/hnp/perl.org/perl_5.42.0/

# 验证
perl -MMath::Random::MT::Auto=rand -e 'print rand(), "\n"'
```
---

**编译结束**: 2026-06-17 16:18
**最终状态**: published
