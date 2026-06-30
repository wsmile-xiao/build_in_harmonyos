# Digest-HMAC 1.05 适配笔记

## 编译环境
- 构建系统: Perl Makefile.PL (ExtUtils::MakeMaker)
- 编译日期: 2026-06-10
- 编译器: N/A (纯 Perl 模块，无编译步骤)
- 状态: published

## 编译步骤

1. 下载源码
```bash
wget http://cpan.metacpan.org/authors/id/A/AR/ARODLAND/Digest-HMAC-1.05.tar.gz
tar xzf Digest-HMAC-1.05.tar.gz
cd Digest-HMAC-1.05
```

2. 生成 Makefile
```bash
perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX
```

3. 编译（纯 Perl 模块，仅复制文件）
```bash
make
```

4. 测试
```bash
make test
# 结果: All tests successful (14 tests)
```

5. 安装到 staging
```bash
make install DESTDIR=$TEST_PREFIX
```

6. 安装到本地
```bash
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile.PL 不接受 --prefix 参数 | Perl 模块使用 INSTALL_BASE 而非 --prefix | 使用 `INSTALL_BASE=$DEFAULT_PREFIX` |
| 2 | 模块加载失败 | 依赖 Digest::SHA1 未安装 | 记录为运行时依赖，需要用户预先安装 |

## 源码修改

无修改，纯 Perl 模块直接编译通过。

## 依赖版本

- Perl 5.42.0 (系统预装)
- Digest::SHA1 (运行时依赖，需预先安装)

## 验证结果

```bash
# 测试结果
t/rfc2202.t .. ok
All tests successful.
Files=1, Tests=14,  0 wallclock secs
Result: PASS

# 模块加载测试（需要先安装 Digest::SHA1）
perl -I$DEFAULT_PREFIX/lib/perl5 -MDigest::HMAC -e 'print $Digest::HMAC::VERSION'
# 输出: 1.05
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| Digest-HMAC-1.05-ohos-aarch64.tar.gz | 14KB | 预编译包 |

## 注意事项

1. **纯 Perl 模块**: 本模块为纯 Perl 实现，无 XS 组件，编译过程简单。
2. **运行时依赖**: 使用此模块需要先安装 Digest::SHA1 模块。
3. **Perl 路径**: 安装后需要设置 `PERL5LIB` 环境变量或在代码中使用 `use lib` 指定路径。

## 功能验证记录

**验证日期**: 2026-06-10

### 测试结果
- HMAC-MD5 RFC 2202 Test Case 1: ✅ PASS
- HMAC-SHA1 RFC 2202 Test Case 1: ✅ PASS
- OpenSSL 结果对比: ✅ 一致
- 模块加载测试: ✅ PASS

### 依赖发现
- Digest::HMAC_SHA1 实际使用 Digest::SHA (Perl内置) 而非 Digest::SHA1 (CPAN)
- Perl 5.42+ 已内置 Digest::SHA v6.04 和 Digest::MD5 v2.59
- 无需额外安装依赖

### 平台可用性
**完全可用** - 纯 Perl 模块，无 XS 组件，无需处理 SELinux/XS 问题

---

**编译结束**: 2026-06-10 18:20
**最终状态**: published
