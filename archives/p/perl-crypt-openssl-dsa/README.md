# Crypt::OpenSSL::DSA

Perl 模块，提供 DSA（Digital Signature Algorithm）签名和验证功能。

## 简介

Crypt::OpenSSL::DSA 是 Perl 的 OpenSSL DSA 绑定模块，提供：
- DSA 密钥生成
- DSA 签名创建
- DSA 签名验证
- PEM 格式的密钥导出/导入

## 已编译版本

| 版本 | 状态 | 发布日期 |
|------|------|---------|
| 0.20 | published | 2026-05-22 |

## 安装方法

### 方法 1：使用预编译包

```bash
# 从 GitCode 下载预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/perl-crypt-openssl-dsa-0.20-ohos-aarch64.tar.gz -O

# 解压到 ~/usr/local
tar xzf perl-crypt-openssl-dsa-0.20-ohos-aarch64.tar.gz -C ~/usr/local

# 设置 PERL5LIB 环境变量
export PERL5LIB="$HOME/usr/local/lib/site_perl/5.42.0/aarch64-linux:$PERL5LIB"

# 验证安装
perl -e "use Crypt::OpenSSL::DSA; print 'OK\n';"
```

### 方法 2：从源码编译

参见版本级归档目录中的 `notes.md`。

## 依赖

- Perl 5.42.0+
- OpenSSL 3.5.6+

## 已知问题

- 用户安装目录下的 .so 文件可能因 SELinux 限制无法加载（平台限制 E046）
- 建议在系统目录安装或等待平台限制解除

## 授权协议

- Perl 模块：Artistic License 2.0
- OpenSSL 绑定：OpenSSL License

## 链接

- CPAN：https://metacpan.org/pod/Crypt::OpenSSL::DSA
- OpenSSL：https://www.openssl.org/