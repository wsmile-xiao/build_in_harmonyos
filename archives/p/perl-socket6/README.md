# perl-socket6

Perl XS module for IPv6 socket support (Socket6).

## 软件信息

- **官网**: https://metacpan.org/release/Socket6
- **许可证**: BSD-3-Clause
- **分类**: network

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 0.29 | built | 2026-07-01 | 首次编译成功，conan-verify 全部通过 |

## 运行依赖

- perl

## 编译依赖

- perl (ExtUtils::MakeMaker)

## 使用说明

Socket6 是 Perl 的 IPv6 socket 支持模块，提供 `getaddrinfo`、`getnameinfo`、
`inet_pton`、`inet_ntop` 等 IPv6 网络函数。

### 安装

预编译包安装到 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/` 目录：
- `Socket6.pm` → Perl 模块文件
- `auto/Socket6/Socket6.so` → XS 共享库

### 注意事项

由于 SELinux HMDFS 限制，XS 模块需要安装到系统目录 `/data/service/hnp` 才能正常加载。
从用户目录或 /dev/shm 加载 .so 会被 MAC 策略阻止（Permission denied）。

### 关键编译适配

1. **autotools configure 绕过**: config.status 在 HMDFS 上失败，手动创建 config.pl 和 config.h
2. **CRT 文件缺失**: 链接参数 `-nostartfiles -nodefaultlibs -lc`（与 perl-dbd-pg 经验一致）
3. **configure 权限**: 解压后需 `chmod +x configure`

---
*OpenHarmony 编译归档 · 2026-07-01*
