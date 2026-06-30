# perl-mail-domainkeys 1.0 适配笔记

## 编译环境
- 构建系统: Perl Makefile.PL (ExtUtils::MakeMaker)
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: built

## 模块说明

Mail::DomainKeys 是 Yahoo DomainKeys 邮件签名协议的 Perl 实现。
⚠️ **作者已声明模块 UNSUPPORTED**，建议迁移到 Mail::DKIM。

## 编译步骤

```bash
# 1. 下载源码
wget https://cpan.metacpan.org/authors/id/A/AD/ADURSO/Mail-DomainKeys-1.0.tar.gz

# 2. 解压
tar xzf Mail-DomainKeys-1.0.tar.gz
cd Mail-DomainKeys-1.0

# 3. 配置
perl Makefile.PL PREFIX=$DEFAULT_PREFIX

# 4. 编译（无 XS 模块，纯 Perl）
make

# 5. 安装
make install DESTDIR=$TEST_PREFIX

# 6. 打包
python3 $SKILL_ROOT/scripts/ohc-run.py package perl-mail-domainkeys 1.0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Crypt::OpenSSL::RSA 缺失 | 运行时依赖 XS 模块 | 需先编译 Crypt-OpenSSL-RSA |
| 2 | XS 模块无法加载 | SELinux HMDFS 限制 | 需管理员安装到系统目录 |

## 依赖分析

### META.yml 依赖

```yaml
requires:
    Crypt::OpenSSL::RSA:    0     # ← XS 模块（关键）
    Mail::Address:          0     # ← ✅ 已满足
    MIME::Base64:           0     # ← ✅ 已满足
    Net::DNS:               0.34  # ← ✅ 已满足 (1.55)
    Test::More:             0     # ← ✅ 已满足
```

### 依赖链

```
Mail::DomainKeys::Message
  └─ Mail::DomainKeys::Signature
      └─ Mail::DomainKeys::Key::Public
          └─ Crypt::OpenSSL::RSA (XS) ← ❌ HMDFS SELinux 限制
```

## 运行时限制

### XS 模块加载问题

Crypt::OpenSSL::RSA 和 Crypt::OpenSSL::Random 是 XS 模块，
安装在 `~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Crypt/OpenSSL/`

SELinux context: `u:object_r:hmdfs:s0`
hishell_hap domain 只能加载 `hnp_file` 类型文件 → Permission denied

### 解决方案

参考 perl-dbd-pg 的经验：
1. 创建 HNP 包
2. 管理员安装到 `/data/service/hnp/perl.org/perl_5.42.0/`
3. 重新签名获得正确的 SELinux type

## 验证结果

```bash
# 主模块加载
perl -MMail::DomainKeys -e 'print $Mail::DomainKeys::VERSION'
# 输出: 1.0 ✅

# 纯 Perl 依赖
perl -MMIME::Base64 -e 'print $MIME::Base64::VERSION'   → 3.16_01 ✅
perl -MMail::Address -e 'print $Mail::Address::VERSION' → 2.22 ✅
perl -MNet::DNS -e 'print $Net::DNS::VERSION'           → 1.55 ✅

# XS 模块依赖
perl -MCrypt::OpenSSL::RSA -e '...'                     → Permission denied ❌
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-mail-domainkeys-1.0-ohos-aarch64.tar.gz | 41KB | 预编译包 |

预编译包内容：
- 8 个 Perl 模块文件（DomainKeys.pm, Message.pm, Signature.pm 等）
- 无 XS 二进制文件（纯 Perl）

## 注意事项

1. **模块弃用**: 作者已声明 UNSUPPORTED，推荐使用 Mail::DKIM
2. **XS 依赖**: 需要先完成 Crypt::OpenSSL::RSA 和 Crypt::OpenSSL::Random 的安装
3. **替代方案**: perl-mail-dkim 1.20240923 已有归档，推荐迁移

## 替代方案推荐

Mail::DKIM 是现代 DomainKeys Identified Mail 实现：
- 版本: 1.20240923
- 状态: 已归档
- 支持 DKIM 签名和验证（比 DomainKeys 更广泛采用）