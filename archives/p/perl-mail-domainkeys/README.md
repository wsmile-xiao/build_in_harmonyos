# Mail::DomainKeys

Yahoo DomainKeys 邮件签名协议的 Perl 实现。

## ⚠️ 弃用声明

**作者已声明此模块 UNSUPPORTED**，建议迁移到 Mail::DKIM。

原文引用（来自 DomainKeys.pm）：
```
THIS MODULE IS OFFICIALLY UNSUPPORTED.

Please move on to DKIM like a responsible Internet user. I have.
It is apparent that DK will not be the way of the future.
```

## 推荐替代方案

使用 **Mail::DKIM** 代替：
- 版本: 1.20240923
- 状态: 已归档（archives/p/perl-mail-dkim/1.20240923）
- DKIM 是现代邮件签名标准，比 DomainKeys 更广泛采用

## 功能说明

Mail::DomainKeys 实现 Yahoo 的邮件签名协议（DomainKeys draft 03）：
- 邮件签名验证
- DomainKeys 签名生成
- RSA 公钥/私钥操作

## 编译版本

- 版本: 1.0
- 编译日期: 2026-06-15
- 状态: built
- 预编译包: perl-mail-domainkeys-1.0-ohos-aarch64.tar.gz (41KB)

## 运行时依赖

### 纯 Perl 依赖（已满足）

| 模块 | 版本 | 状态 |
|-----|------|------|
| MIME::Base64 | 3.16+ | ✅ |
| Mail::Address | 2.22+ | ✅ |
| Net::DNS | 0.34+ | ✅ |
| Test::More | 任意 | ✅ |

### XS 模块依赖（需管理员安装）

| 模块 | 状态 | 说明 |
|-----|------|------|
| Crypt::OpenSSL::RSA | ❌ | 需安装到系统目录 |
| Crypt::OpenSSL::Random | ❌ | 需安装到系统目录 |

⚠️ **XS 模块受 SELinux HMDFS 限制**，在 `~/usr/local` 下无法加载。
需要管理员将 XS 模块安装到 `/data/service/hnp/` 系统目录。

## 安装方式

```bash
# 解压预编译包到 Perl site_perl 目录
tar xzf perl-mail-domainkeys-1.0-ohos-aarch64.tar.gz -C ~/usr/local/lib
```

⚠️ 安装后需要单独处理 XS 依赖模块。

## 版本索引

| 版本 | 编译日期 | 状态 |
|------|---------|------|
| 1.0 | 2026-06-15 | built |

## 相关模块

- perl-mail-dkim: DomainKeys Identified Mail（推荐）
- Crypt-OpenSSL-RSA: RSA 加密模块（XS）
- Crypt-OpenSSL-Random: 随机数生成（XS）