# Crypt::PBKDF2 for HarmonyOS

Crypt::PBKDF2 是一个纯 Perl 实现的 PBKDF2 (Password-Based Key Derivation Function 2) 密码哈希模块，实现 RFC 2898 标准的 PBKDF2 算法，支持 HMAC-SHA1/SHA2/SHA3 作为伪随机函数。

## 功能概述

- **PBKDF2 密码哈希**：从密码和 salt 派生密钥，支持自定义迭代次数和输出长度
- **多算法支持**：HMAC-SHA1、HMAC-SHA256、HMAC-SHA512、HMAC-SHA3（SHA3 鸿蒙受限）
- **双编码格式**：LDAP 格式 (`{X-PBKDF2}...`) 和 crypt 格式 (`$PBKDF2$...`)
- **generate/validate 接口**：一键生成哈希和验证密码
- **RFC 6070 兼容**：标准测试向量全部通过

## OHOS 适配

### 构建方式

纯 Perl 模块，使用 ExtUtils::MakeMaker (Makefile.PL) 构建，无需 C 编译器：

```bash
perl Makefile.PL && make && make test && make install
```

### 已知问题与限制

| 问题 | 影响 | 变通方案 |
|------|------|---------|
| XS .so 无法从 HMDFS 加载 | HMAC-SHA3 不可用 | 使用 HMAC-SHA1/SHA256/SHA512 替代 |
| B::Hooks::EndOfScope XS 不可用 | 无直接影响 | 设置 `PERL_B_HOOKS_ENDOFSCOPE_BACKEND=PP` |
| cpanm 不可用 (prctl bug) | 无法自动安装依赖 | 手动从 CPAN 下载安装 |
| /tmp 只读 | 临时文件写入失败 | 使用 `$TMPDIR` 或 `$HOME/tmp` |

### 可用功能矩阵

| 功能 | 状态 |
|------|------|
| HMAC-SHA1 | ✅ 可用 |
| HMAC-SHA256 | ✅ 可用 |
| HMAC-SHA512 | ✅ 可用 |
| HMAC-SHA3 | ❌ 不可用 (XS 限制) |
| LDAP 编码 | ✅ 可用 |
| Crypt 编码 | ✅ 可用 |

## 依赖关系

### 编译依赖
- Perl 5.42.0+
- Conan 2.29.1 (OHOS 适配版)

### 运行时依赖 (CPAN 管理，不在 Conan 中)
- Moo, Type::Tiny, Try::Tiny, Module::Runtime
- Digest::HMAC, namespace::autoclean, strictures
- B::Hooks::EndOfScope (PP 后端)

## 使用方法

```bash
# 安装 Conan 包
conan install --requires=perl-crypt-pbkdf2/0.161520-r1@ohpcd/stable

# 设置环境
export PERL5LIB="<conan_package>/lib/perl5:$HOME/perl5/lib/perl5"
export PERL_B_HOOKS_ENDOFSCOPE_BACKEND=PP

# 使用
perl -e '
  use Crypt::PBKDF2;
  my $pbkdf2 = Crypt::PBKDF2->new(
    hash_class => "HMACSHA1",
    iterations => 1000,
  );
  my $hash = $pbkdf2->generate("mypassword");
  print "Hash: $hash\n";
  print "Valid: ", $pbkdf2->validate($hash, "mypassword"), "\n";
'
```

## 版本列表

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.161520-r1 | built | 2026-07-06 |

## 参考资料

- [CPAN: Crypt-PBKDF2](https://metacpan.org/dist/Crypt-PBKDF2)
- [RFC 2898: PKCS #5 PBKDF2](https://tools.ietf.org/html/rfc2898)
- [RFC 6070: PBKDF2 Test Vectors](https://tools.ietf.org/html/rfc6070)
