# Digest::SHA3

## 简介

Digest::SHA3 是 Perl 的 SHA-3 摘要算法模块，实现了 NIST FIPS 202 标准中定义的 SHA-3 和 SHAKE 算法。这是一个 XS 模块，用 C 语言实现以获得高性能。

## 版本信息

- **当前版本**: 1.01
- **发布日期**: 2017-10-22
- **作者**: Mark Shelor (MSHELOR)
- **CPAN**: https://metacpan.org/pod/Digest::SHA3

## 编译状态

| 版本 | 状态 | 编译日期 | 功能验证 | 备注 |
|------|------|---------|---------|------|
| 1.01 | built | 2026-06-10 | ⚠️ **未验证** | XS模块已签名，功能未确认 |

### ⚠️ 重要警告

**本模块当前不承诺SHA-3功能可用**

- 编译验证通过：ELF结构正常、已签名
- **功能验证阻塞**：SELinux HMDFS限制 + 无installs权限
- **未验证风险**：
  - ❌ SHA-3算法输出正确性未验证（未测试任何标准值）
  - ❌ 所有API函数可用性未确认
  - ❌ 运行时链接库依赖未验证

**实际可用性需管理员安装后确认**

## 平台限制

- **SELinux HMDFS 限制**: XS 模块无法从用户目录加载
- **解决方案**: 安装到系统目录 `/data/service/hnp/perl.org/perl_5.42.0/`

## 安装方法

管理员安装步骤：

```bash
sudo -u installs unzip perl-digest-sha3-1.01-ohos-aarch64.hnp -d /data/service/hnp/perl.org/perl_5.42.0/
perl -MDigest::SHA3 -e 'print sha3_256_hex("test"), "\n"'
```

## 相关模块

- Digest::MD5 - MD5 摘要（已验证可用）
- Digest::SHA - SHA-2 摘要

## 维护者

OpenHarmonyPCDeveloper Team