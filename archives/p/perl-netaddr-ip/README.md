# perl-netaddr-ip

Perl XS 模块：IPv4 和 IPv6 地址及子网管理。

## 描述

NetAddr::IP 是一个 Perl 模块，用于管理 IPv4 和 IPv6 地址和子网。它提供了完整的 IP 地址操作功能，包括地址计算、子网划分、范围检查等。包含 XS 加速组件 (Util.so) 提供 128 位整数运算的高性能实现。

## 版本信息

- 当前版本：4.079-r14
- CPAN 上游版本：4.079
- 发布日期：2026-07-01

## 构建系统

- 构建系统类型：Perl ExtUtils::MakeMaker (Makefile.PL) — custom
- 模块类型：XS (C 扩展，Util.so)
- 编译器：clang 18.1.8 (OHOS SDK)

## 依赖

- perl 5.42.0 (HNP 预装)
- 无外部库依赖 (Util.so 仅链接 libc.so)

## OHOS 适配

### 关键适配点

1. **CPATH 环境变量**：conan 构建环境不继承 shell CPATH，需在 conanfile.py build() 中显式设置 musl/sysroot include 路径
2. **config.h 手动创建**：HMDFS 上 config.status 无法创建临时文件，根据 configure 检测结果手动创建
3. **XS 模式强制**：使用 `--xs` 参数确保生成 Util.so 而非纯 Perl 回退
4. **Socket6 干扰处理**：系统 Socket6 缺少 gethostbyname2 导出，test_package 中过滤 site_perl 路径

### 已知平台限制

- HMDFS SELinux 标记 `u:object_r:hmdfs:s0`，不影响 Conan 包使用
- 系统 Socket6 模块不导出 gethostbyname2/getipnodebyname（Conan 包通过 Util.pm 回退机制规避）

## 编译状态

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 4.079-r14 | built | 2026-07-01 | XS 模式，conan-verify 全部通过 (G1-G4, L2, L4, L5) |

## conan-verify 结果

```
G1: ✅ PASS  配方完整性检查
G2: ✅ PASS  conan create (干净构建 + test_package)
G3: ✅ PASS  系统同名库隔离 (R26)
G4: ✅ PASS  产物完整性 (1 .so)
L2: ✅ PASS  平台功能矩阵
L4: ✅ PASS  静态安全扫描 (NX, PIE, RELRO, CANARY)
L5: ✅ PASS  产物基线对比
```

## 产物信息

- **Util.so**: ELF 64-bit AArch64, ~30KB
  - 路径: lib/aarch64-linux/auto/NetAddr/IP/Util/Util.so
  - 依赖: libc.so (仅此一个)
  - 安全特性: Full RELRO, NX enabled, PIE enabled, Stack Canary enabled

## 安装说明

通过 Conan 安装：

```bash
conan install --requires=perl-netaddr-ip/4.079-r14@ohpcd/stable -pr:h=ohos-aarch64 --build=missing
```

安装后验证：

```perl
use NetAddr::IP;
my $ip = NetAddr::IP->new('192.168.1.1/24');
print "$ip\n";  # 192.168.1.1/24
```

## 功能特性

- IPv4 和 IPv6 地址对象创建和管理
- 子网计算和网络地址识别
- 地址范围检查和包含判断
- CIDR 格式支持
- XS 加速的 128 位整数运算 (Util.so)
- 纯 Perl 回退机制 (Socket6 不可用时)

## 许可证

GPL-2.0-only or Artistic-1.0 (Perl 双许可证)

## 来源

- CPAN: https://cpan.metacpan.org/authors/id/M/MI/MIKER/NetAddr-IP-4.079.tar.gz
