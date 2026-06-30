# JSON::WebToken

## 简介

JSON::WebToken 是一个 Perl 模块，用于 JSON Web Token (JWT) 的编码和解码。JWT 是一种开放标准 (RFC 7519)，用于在各方之间安全地传输信息作为 JSON 对象。

## 功能概述

- **JWT 编码**: 支持标准 JWT claims 编码 (iss, sub, aud, exp, nbf, iat, jti)
- **JWT 解码**: 支持 JWT 解码和签名验证
- **算法支持**: HS256 (HMAC SHA-256), RS256 (RSA SHA-256) 等签名算法
- **错误处理**: 提供完善的异常处理机制

## OHOS 适配

### 适配要点

1. **构建系统**: 源码使用 Module::Build，但系统缺少该模块，改用 ExtUtils::MakeMaker (Makefile.PL)
2. **纯 Perl 模块**: 无 XS 编译，无需处理 C 代码链接问题
3. **无加载限制**: 作为纯 Perl 模块，不受 HMDFS 限制，用户可直接使用
4. **依赖完整**: 所有运行时依赖已安装并可用

### 与 Linux 的差异

| 项目 | Linux | OpenHarmony |
|------|-------|-------------|
| 构建系统 | Build.PL (Module::Build) | Makefile.PL (ExtUtils::MakeMaker) |
| XS 模块 | 正常加载 | HMDFS 限制 (纯 Perl 模块不受影响) |
| 用户安装 | 可用 | 可用，无限制 |

### 已知问题

- **测试依赖缺失**: Test::Requires, Test::Mock::Guard 等测试模块未安装，但不影响核心功能

## 排除与替代

无排除项，该模块功能完整且可用。

## 依赖

### 编译依赖
- Perl 5.42.0
- ExtUtils::MakeMaker (系统自带)

### 运行时依赖
- JSON (≥ 4.11)
- Module::Runtime (≥ 0.018)
- Digest::SHA (≥ 6.04)
- MIME::Base64 (≥ 3.16)
- parent (≥ 0.244)

所有运行时依赖均已安装并可用。

## 功能验证

### 测试结果 (2026-06-13)

| 测试项 | 状态 |
|-------|------|
| 模块加载 | ✅ PASS |
| JWT 编码 | ✅ PASS |
| JWT 解码 | ✅ PASS |
| 数据完整性 | ✅ PASS |
| 错误处理 | ✅ PASS |
| 质量门禁 | ✅ PASS |

### 使用示例

```perl
use JSON::WebToken;

# JWT 编码
my $claims = {
    iss => "user_id",
    exp => time() + 3600,  # 1 小时后过期
    data => { role => "admin" }
};
my $jwt = encode_jwt($claims, "secret_key");

# JWT 解码
my $decoded = decode_jwt($jwt, "secret_key");
print "Issuer: $decoded->{iss}\n";
```

## 安装指南

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | \
  sh -s -- perl-json-webtoken 0.10-r5

# 验证安装
perl -I~/usr/local/lib/perl5/site_perl -I~/usr/local/lib/perl5 \
  -MJSON::WebToken -e 'print $JSON::WebToken::VERSION'
# 输出: 0.10
```

## 参考资料链接

- **CPAN**: https://metacpan.org/pod/JSON::WebToken
- **源码仓库**: https://github.com/xaicron/JSON-WebToken
- **JWT RFC**: https://tools.ietf.org/html/rfc7519
- **编译归档**: archives/p/perl-json-webtoken/0.10-r5/

## 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.10-r5 | published | 2026-06-12 | 首次适配成功，功能验证通过 |

---

**维护者**: OpenHarmony 编译团队
**最后更新**: 2026-06-13