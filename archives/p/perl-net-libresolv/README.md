# perl-net-libresolv

libresolv（DNS 解析器函数）的 Perl XS 封装。

## 简介

Net::LibResolv 提供 Perl 对 DNS 解析器函数 `res_query`、`res_search`、
`res_mkquery`、`dn_expand` 和 `dn_skipname` 的访问能力。在 musl/HarmonyOS 上，
这些函数直接内置于 libc（无需独立的 libresolv 库）。

## 版本

| 版本 | 状态 | 日期 | 备注 |
|------|------|------|------|
| 0.03-r2 | built | 2026-06-29 | Conan 验证通过，HNP 安装包可用 |

## 构建系统

自定义 Perl XS 构建（xsubpp → clang -c → clang -shared）。

标准的 `perl Build.PL` / `ExtUtils::CChecker` 方式在 HarmonyOS 上会失败，原因是
libpth 过时且 ld.lld 无法识别 `-fstack-protector-strong`。conanfile.py 通过直接
调用 xsubpp 和 clang 绕过了此问题。

## 补丁

1. **0001-Build.PL.patch** — 用直接 Module::Build 替换 ExtUtils::CChecker；修复 musl/HarmonyOS 的头文件/库路径
2. **0002-lib-Net-LibResolv.xs.patch** — 添加 `PROTOTYPES: DISABLE` 以抑制 xsubpp 警告

## 平台说明

### SELinux HMDFS 限制

HMDFS 文件系统上的 .so 文件 SELinux 上下文为 `hmdfs:s0`。以 `hishell_hap` 域
运行的 Perl 进程只能加载 `hnp_file` 类型的文件。这导致运行时加载 .so 报
"Permission denied"。

**解决方案**: 使用管理员用户将 HNP 包安装到系统目录（`/data/service/hnp/`），
然后用 `binary-sign-tool` 重新签名。

### musl libresolv

在 musl/HarmonyOS 上，`res_query` 和 `res_search` 直接内置于 libc。桩文件
`libresolv.a`（8 字节）不提供任何符号。.so 链接时不使用 `-lresolv`。

## 安装

```bash
# 使用 HNP 包安装（需管理员权限）
sudo -u installs unzip perl-net-libresolv.hnp -d /data/service/hnp/perl.org/perl_5.42.0/

# 重新签名以获得正确的 SELinux 类型
/data/service/hnp/bin/binary-sign-tool sign \
  -inFile /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Net/LibResolv/LibResolv.so \
  -outFile /tmp/LibResolv.so.signed -selfSign 1

sudo -u installs mv /tmp/LibResolv.so.signed \
  /data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0/aarch64-linux/auto/Net/LibResolv/LibResolv.so
```

## 用法

```perl
use Net::LibResolv qw(
    res_query res_search res_mkquery
    dn_expand dn_skipname
    h_errno
    C_IN C_CHAOS C_HS C_NONE
    T_A T_NS T_MD T_MF T_CNAME T_SOA T_MB T_MG T_MR T_NULL T_WKS T_PTR T_HINFO T_MINFO T_MX T_TXT
);

my @answer = res_query("example.com", C_IN, T_A);
print "DNS 查询返回 " . scalar(@answer) . " 字节\n";
```
